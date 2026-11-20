from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .res_partner import CANALES_VENTA

MONTO_APROBACION = 50000
ESTADOS_COTIZACION = ("draft", "sent")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    canal_venta = fields.Selection(
        CANALES_VENTA,
        string="Canal de venta",
        compute="_compute_canal_venta",
        store=True,
        readonly=False,
    )
    total_unidades = fields.Float(
        string="Total de unidades",
        compute="_compute_total_unidades",
        store=True,
    )
    requiere_aprobacion = fields.Boolean(
        string="Requiere aprobación",
        compute="_compute_requiere_aprobacion",
        store=True,
    )
    aprobado_por = fields.Many2one(
        "res.users",
        string="Aprobado por",
        readonly=True,
        copy=False,
    )
    pendiente_aprobacion = fields.Boolean(
        compute="_compute_pendiente_aprobacion",
    )

    @api.depends("partner_id")
    def _compute_canal_venta(self):
        for order in self:
            order.canal_venta = order.partner_id.canal_preferido

    @api.depends(
        "order_line.product_uom_qty", "order_line.display_type",
        "order_line.product_id", "order_line.is_downpayment",
    )
    def _compute_total_unidades(self):
        for order in self:
            order.total_unidades = sum(
                line.product_uom_qty for line in order.order_line
                if line.product_id and not line.display_type and not line.is_downpayment
            )

    @api.depends("amount_total")
    def _compute_requiere_aprobacion(self):
        for order in self:
            order.requiere_aprobacion = order.amount_total > MONTO_APROBACION

    @api.depends("requiere_aprobacion", "aprobado_por", "state")
    def _compute_pendiente_aprobacion(self):
        for order in self:
            order.pendiente_aprobacion = (
                order.requiere_aprobacion
                and not order.aprobado_por
                and order.state in ESTADOS_COTIZACION
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("aprobado_por") for vals in vals_list):
            raise AccessError(self.env._("Usa el botón Aprobar para registrar una aprobación."))
        orders = super().create([dict(vals, aprobado_por=False) for vals in vals_list])
        orders.filtered(lambda order: order.state == "sale")._check_aprobacion()
        return orders

    def write(self, vals):
        if "aprobado_por" in vals:
            raise AccessError(self.env._("Usa el botón Aprobar para registrar una aprobación."))
        totales_antes = self._totales_aprobados()
        por_confirmar = self.browse()
        if vals.get("state") == "sale":
            por_confirmar = self.filtered(lambda order: order.state != "sale")
        res = super().write(vals)
        self._anular_aprobacion_si_cambio_total(totales_antes)
        por_confirmar._check_aprobacion()
        return res

    def _totales_aprobados(self):
        return {
            order.id: (order.amount_total, order.currency_id)
            for order in self if order.aprobado_por
        }

    def _anular_aprobacion_si_cambio_total(self, totales_antes):
        cambiados = self.filtered(
            lambda order: order.id in totales_antes
            and (order.amount_total, order.currency_id) != totales_antes[order.id]
        )
        if cambiados:
            super(SaleOrder, cambiados).write({"aprobado_por": False})

    @api.constrains("canal_venta", "partner_id")
    def _check_canal_distribuidor(self):
        """Reto 2: el canal Distribuidor solo se permite a clientes empresa."""
        for order in self:
            if (
                order.canal_venta == "distribuidor"
                and order.partner_id
                and not order.partner_id.is_company
            ):
                raise ValidationError(
                    f"El canal Distribuidor solo se permite para clientes "
                    f"empresa. {order.partner_id.name} no es una empresa."
                )


    def action_aprobar(self):
        if not self.env.user.has_group("sales_team.group_sale_manager"):
            raise AccessError(self.env._("Solo un administrador de ventas puede aprobar pedidos."))
        if self.filtered(lambda order: not order.pendiente_aprobacion):
            raise UserError(self.env._("Solo se pueden aprobar cotizaciones pendientes de aprobación."))
        super().write({"aprobado_por": self.env.user.id})
        return True

    def _check_aprobacion(self):
        for order in self:
            if order.requiere_aprobacion and not order.aprobado_por:
                raise UserError(self.env._(
                    "El pedido %(pedido)s supera %(monto)s y requiere la aprobación de un administrador de ventas.",
                    pedido=order.display_name, monto=f"{MONTO_APROBACION:,}",
                ))

    def action_confirm(self):
        self._check_aprobacion()
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        default_order_id = self.default_get(["order_id"]).get("order_id")
        order_ids = {vals.get("order_id", default_order_id) for vals in vals_list}
        orders = self.env["sale.order"].browse([order_id for order_id in order_ids if order_id])
        totales_antes = orders._totales_aprobados()
        lines = super().create(vals_list)
        orders._anular_aprobacion_si_cambio_total(totales_antes)
        return lines

    def write(self, vals):
        orders = self.order_id | self.env["sale.order"].browse(vals.get("order_id") or [])
        totales_antes = orders._totales_aprobados()
        res = super().write(vals)
        orders._anular_aprobacion_si_cambio_total(totales_antes)
        return res

    def unlink(self):
        orders = self.order_id
        totales_antes = orders._totales_aprobados()
        res = super().unlink()
        orders._anular_aprobacion_si_cambio_total(totales_antes)
        return res
