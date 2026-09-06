# Pasarela de Pago - Ahhh! Ibiza

Documento de referencia del sistema de compra online de Tangas. Explica como
funciona la arquitectura, como se anade una pasarela real nueva y que queda
pendiente antes de cobrar de verdad.

Ver tambien: `docs/roadmap.md` (fase de pagos), `docs/state_of_play.md`
(estado actual) y `docs/despliegue.md` (entorno y variables).

## Que es este sistema

Los profesionales compran paquetes de Tangas con euros. El dinero entra por una
pasarela de pago y el saldo interno del profesional (Tangas) se acredita cuando
la pasarela confirma el cobro.

- `TangasPackage`: paquetes que se compran (ej: 50 T por 15 EUR). Son el "precio
  de entrada" del dinero.
- `RechargeOrder`: una orden de recarga. Se crea PENDING, pasa a PAID cuando la
  pasarela confirma el pago, o a FAILED/CANCELLED.
- `Transaction`: registro contable del movimiento de saldo. Cada recarga pagada
  crea una transaccion enlazada a su orden.
- `PromotionProduct`: gasto de Tangas dentro de la plataforma (promocionar
  anuncios). No es una pasarela: consume saldo ya acreditado.

Los dos tipos no se mezclan: los paquetes compran Tangas, las promociones las
gastan. La pasarela solo participa en la primera parte.

## Arquitectura

La pasarela se aisla detras de una interfaz comun, de forma que el resto del
sistema (ordenes, saldo, transacciones) no sabe que pasarela concreta esta
activa. La pasarela activa se elige por configuracion, sin tocar codigo.

```
templates/payments/dummy_checkout.html  (checkout simulado, solo dummy)
        |
        v
apps/payments/views.py: recharge_start
        |  crea la orden y pide la URL de pago a la pasarela
        v
gateways/<pasarela>.py  (BaseGateway)
        |  devuelve checkout_url + gateway_order_id
        v
Usuario paga en la pasarela (o en la pagina simulada de dummy)
        |
        v  la pasarela notifica el resultado
apps/payments/views.py: payment_webhook  (csrf_exempt, firma)
        |
        v
services.py: confirm_payment / fail_payment  (transaction.atomic)
        v
Saldo acreditado + Transaction + orden PAID  (idempotente)
```

Piezas clave:

- `gateways/base.py`: `BaseGateway`, la interfaz que toda pasarela debe
  implementar. Tres metodos: `create_checkout`, `verify_webhook` y
  `parse_event`.
- `gateways/dummy.py`: `DummyGateway`, simulacion para desarrollo. No cobra
  nada. Solo permitida con `AHHH_DEBUG=True` o en tests.
- `gateways/disabled.py`: `DisabledGateway`, para produccion sin pasarela real.
  Bloquea la recarga online (no crea ordenes) y muestra un mensaje claro; el
  superadmin sigue pudiendo ajustar saldo manualmente desde el panel.
- `gateways/registry.py`: catalogo de pasarelas disponibles (`_GATEWAYS`).
  Bloquea `dummy` en produccion y valida que la pasarela elegida exista.
- `services.py`: toda la logica de negocio. Crea la orden, confirma el pago
  (acredita saldo de forma atomica e idempotente) o lo falla/cancela/reembolsa.
- `views.py`: entrada del usuario (recarga) y entrada de la pasarela (webhook).
- `checks.py`: system check `payments.E001` que avisa si se usa `dummy` en
  produccion.

## Seguridad aplicada

- El importe y las Tangas se copian SIEMPRE de la base de datos
  (`TangasPackage`), nunca de datos enviados por el cliente.
- El webhook verifica que el importe y la moneda declarados por la pasarela
  coinciden con la orden antes de acreditar nada.
- El saldo se acredita con `select_for_update` sobre el usuario y la orden:
  dos webhooks simultaneos no pueden acreditar dos veces ni perder saldo.
- La confirmacion es idempotente: si la orden ya estaba PAID, no se acredita
  otra vez.
- El webhook de las pasarelas reales debe validar la firma del payload
  (`verify_webhook`). El `dummy` no tiene firma y solo existe en desarrollo.
- El webhook esta protegido con `csrf_exempt` porque las pasarelas no envian
  token CSRF; la autenticidad real se apoya en la firma.
- `recharge_start` esta limitado por `django-ratelimit` (30 por 10 minutos).

## Configuracion

Variables en `.env` (ver `.env.example`):

| Variable               | Valores                 | Descripcion                                   |
| ---------------------- | ----------------------- | --------------------------------------------- |
| `AHHH_PAYMENT_GATEWAY` | `dummy`, `disabled`, o nueva | Pasarela activa. `dummy` solo en desarrollo; `disabled` en produccion sin pasarela real (bloquea la recarga). |
| `AHHH_PAYMENT_MODE`    | `test`, `live`          | Modo de operacion. Validado al arrancar.      |
| `AHHH_PUBLIC_BASE_URL` | URL, sin barra final    | Origen publico (ej. `https://www.ahhh-ibiza.com`). Se usa para construir la URL del webhook que configura la pasarela. |

- `test` (sandbox): la pasarela opera sin cobrar, para probar.
- `live`: cobros reales. Al cambiar el modo hay que asegurar que la pasarela
  real esta activa, porque `dummy` se bloquea en produccion.
- `disabled`: no hay pasarela real integrada. Es la opcion para produccion
  mientras tanto: el sitio funciona pero la recarga online muestra "no
  disponible" y no crea ordenes. El panel de control sigue permitiendo al
  superadmin ajustar saldo manualmente.
- `AHHH_PUBLIC_BASE_URL`: en produccion debe apuntar al dominio final con
  HTTPS. En desarrollo local puede dejarse vacio.

Las claves privadas de la pasarela real (secret keys) van en el `.env` local o
del servidor, NUNCA en el repositorio. Solo se versiona `.env.example`.

## URL publica del webhook

El endpoint que la pasarela debe configurar como "webhook URL" es
`/pagos/webhook/`, y en produccion su forma absoluta es:

```
{AHHH_PUBLIC_BASE_URL}/pagos/webhook/
```

El helper `apps/payments/services.py: public_webhook_url()` construye esa URL
desde `AHHH_PUBLIC_BASE_URL` (si no esta definido devuelve solo la ruta
relativa). Es el unico punto de verdad: cuando se conecte una pasarela real,
basta con leer esa URL y configurarla en el panel de la pasarela. La URL
resuelve a `views.payment_webhook`, que ya esta preparada para recibir
notificaciones (csrf_exempt y validacion de firma por pasarela).

## Como anadir una pasarela nueva

1. Crear `apps/payments/gateways/<nombre>.py` con una clase que herede de
   `BaseGateway` e implemente los tres metodos:

   - `create_checkout(order)` -> `{'checkout_url': str, 'gateway_order_id': str}`
   - `verify_webhook(request)` -> `bool` (valida la firma del payload)
   - `parse_event(request)` -> `{'event_type': 'payment.succeeded'|'payment.failed',
     'gateway_order_id': str, 'raw': dict, 'amount': opcional, 'currency': opcional}`

2. Registrar la clase en `_GATEWAYS` de `gateways/registry.py`, por ejemplo:
   `'stripe': StripeGateway`.

3. Elegirla en el `.env`: `AHHH_PAYMENT_GATEWAY=stripe` y `AHHH_PAYMENT_MODE=test`
   (sandbox primero, `live` solo cuando este probada).

4. Conectar el webhook real de la pasarela (HTTPS) a la URL
   `/pagos/webhook/` de la instalacion. La vista `payment_webhook` ya resuelve
   el resto: verifica firma, parsea, localiza la orden, valida importe y
   acredita/falla.

5. Pruebas: reutilizar `RechargeFlowTest` en `apps/payments/tests.py` como
   base. Los tests del flujo no dependen de la pasarela concreta salvo en la
   firma, que la pasarela real debe cubrir con sus propios casos.

El contrato del gateway es minimo a proposito: el `dummy` muestra que todo el
ciclo funciona sin pasarela real, y una pasarela nueva solo tiene que traducir
su API al contrato de `BaseGateway`.

## Pendiente antes de cobrar de verdad

1. **Elegir pasarela adulto-friendly.** El proyecto es un directorio adulto;
   varias pasarelas estandar (Stripe, PayPal) prohiben o restringen este tipo
   de negocio en sus condiciones de servicio. Hay que confirmar que la pasarela
   elegida acepta contenido adulto legal y adultos solo en sus terminos.

2. **HTTPS para el webhook.** Las pasarelas reales exigen que la URL de
   notificacion este en HTTPS con certificado valido. El despliegue de
   `docs/despliegue.md` ya plantea nginx + HTTPS; el webhook debe apuntar a la
   URL publica final (`AHHH_PUBLIC_BASE_URL + /pagos/webhook/`, ver
   `public_webhook_url()`), no a `localhost`.

3. **Firma del webhook.** La pasarela real debe firmar sus notificaciones y
   `verify_webhook` debe comprobarla (el `dummy` devuelve `True` siempre, solo
   desarrollo). Con la firma real se puede reforzar tambien la validacion de
   IPs de origen de la pasarela.

4. **Decisiones de negocio pendientes** (del roadmap): politica de reembolso
   (el stub `refund_order` no descuenta Tangas ya gastadas), precio final de los
   paquetes, impuestos/facturacion si aplican, y periodo de gracia por impago.

## Estado

Implementado y verificado (63 tests de la suite completa, incluyendo
`RechargeFlowTest`): creacion de orden PENDING, checkout dummy, confirmacion
con acreditacion atomica e idempotente, fallo sin acreditacion, cancelacion,
gestion visual de paquetes por superadmin y admin de Django para paquetes,
ordenes y logs. La pasarela real queda pendiente segun el punto anterior.
