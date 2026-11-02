# Integracion con Eupago - guia de implementacion

Plan de trabajo para conectar la pasarela **Eupago** (eupago.pt) al sistema de
recarga de Tangas. Esta documento recoge todo lo necesario para implementarla
**sin tener que volver a escanear el proyecto ni la documentacion externa**:
que ya existe, que hay que crear, decisiones ya tomadas y puntos abiertos.

Ver tambien: `docs/pagos_pasarela.md` (arquitectura general de la pasarela),
`docs/despliegue.md` (entorno y variables), `.env.example` (variables ya
previstas).

## Resumen ejecutivo

- **Dificultad: FACIL.** La arquitectura del proyecto ya esta preparada; solo
  hay que crear un adaptador, registrarlo y configurar variables.
- **Alcance codigo:** 1 archivo nuevo (`gateways/eupago.py`), 1 linea en
  `gateways/registry.py`, variables en `.env`/`.env.example`, tests.
- **NO hay que tocar:** models, services, views, urls ni plantillas.
- **Unico riesgo no tecnico:** confirmar con Eupago que acepta contenido
  adulto legal (punto 0 de la fase 0). Si no lo acepta, este documento no se
  puede aplicar y hay que buscar otra pasarela.
- **Estado (oct. 2026):** visto bueno de la plataforma conseguido; pendiente de
  la fase 0 el KYC y las credenciales. Fases 1 y 2 completas (adaptador +
  registro + variables + tests, **136 en total en verde**), incluido soporte
  de **webhook 1.0 y 2.0**. Se dispone de una **API key de produccion
  verificada** (`201 Success` en `clientes.eupago.pt`); siguen pendientes:
  API key de **sandbox** (las claves no sirven entre entornos) y, solo para
  2.0, la clave de firma del canal ("Chave Criptografica"). Fases 3-4
  bloqueadas por esas credenciales.

## Documentacion oficial vs. realidad comprobada

La doc de Eupago no cubre todo; esto se verifico a mano (oct. 2026):

| Tema | Doc oficial | Realidad |
| ---- | ----------- | -------- |
| API key | "solo cambia `sandbox` por `clientes`" | Hay **clave por entorno**: la de produccion da `401 APIKEY_INVALID` en sandbox; la de pruebas tambien falla en produccion |
| Callback | Guia: marcar casilla + pegar URL | Solo para recibir. Para **validar** el webhook 2.0 hace falta la clave del canal (Webhooks 2.0 panel); la 1.0 no la necesita (valida `chave_api`) |
| `X-Signature` | Ejemplo PHP: HMAC SHA-256 **base64** | **Confirmado en fase 3**: Eupago firma en **base64** sobre el body exacto; con la clave del canal el HMAC coincide |
| Payload 2.0 | `transactions` (plural) | **Confirmado en fase 3**: el aviso real trae `transaction` (**singular**) con `channel` aparte. El parser acepta singular, plural y lista para no depender del formato |
| URL de pago | Dos familias coexisten | Legacy "Body Auth" (`/clientes/rest_api/<metodo>/create`, key en el body) **no tiene PayByLink**; usamos "ApiKey Auth" (`/api/v1.02/paybylink/create`, key en header), verificado con `201 Success` |
| Webhook 1.0 | GET con params; incluye `chave_api` | Solo avisa de pagos realizados (no error/cancelado/expirado); sin HMAC; la key viaja en la URL (queda en logs/proxies) |

## Que ya existe en el proyecto (no reimplementar)

El sistema de pagos esta abstraerto tras una interfaz comun. Piezas ya
resueltas y verificadas (136 tests, incluidos `RechargeFlowTest` y
`EupagoGatewayTest`):

| Pieza | Archivo | Rol |
| ----- | ------- | --- |
| Contrato de pasarela | `apps/payments/gateways/base.py` | `BaseGateway` con `create_checkout`, `verify_webhook`, `parse_event` |
| Registro | `apps/payments/gateways/registry.py` | `_GATEWAYS`; elegir pasarela con `AHHH_PAYMENT_GATEWAY` |
| Referencias existentes | `apps/payments/gateways/dummy.py`, `disabled.py` | Ejemplos de implementacion (dummy solo dev) |
| Logica de negocio | `apps/payments/services.py` | Crea orden, `start_checkout`, confirma/falla pago atomico e idempotente, valida importe y moneda |
| Webhook | `apps/payments/views.py: payment_webhook` | Endpoint `/pagos/webhook/` (`csrf_exempt`, valida firma via gateway, parsea, acredita) |
| URL publica del webhook | `apps/payments/services.py: public_webhook_url()` | Construye `{AHHH_PUBLIC_BASE_URL}/pagos/webhook/` |
| Tests reutilizables | `apps/payments/tests.py: RechargeFlowTest` | Flujo completo; solo la firma varia por pasarela |

Flujo ya cableado (no modifica):

```
recharge_start -> services.create_recharge_order -> services.start_checkout
  -> gateway.create_checkout(order) -> redirect(checkout_url)
  -> (usuario paga en Eupago)
  -> Eupago llama a /pagos/webhook/ -> gateway.verify_webhook
  -> gateway.parse_event -> services.confirm_payment / fail_payment
  -> saldo acreditado + Transaction + orden PAID (idempotente)
```

## Referencia Eupago (lo esencial)

Fuentes oficiales (consulta solo si algo cambia):

- Integracion REST: <https://eupago.readme.io/reference/api-eupago>
- Pay By Link: <https://eupago.readme.io/reference/paybylink>
- Webhooks 2.0: <https://eupago.readme.io/reference/realtime-webhooks-20>
- Indice completo (LLMs): <https://eupago.readme.io/llms.txt> (anadir `.md`
  a cualquier pagina para obtener su markdown)

### Entornos

| Entorno | Base URL |
| ------- | -------- |
| Sandbox (pruebas) | `https://sandbox.eupago.pt/api/` |
| Produccion | `https://clientes.eupago.pt/api/` |

El cambio entre entornos es sustituir `sandbox` por `clientes`. El proyecto ya
tiene el concepto de modo con `AHHH_PAYMENT_MODE=test|live`: usar `test` =>
sandbox, `live` => produccion.

### Autenticacion

Header HTTP: `Authorization: ApiKey <API_KEY>` (la API Key esta en el
backoffice de Eupago, menu *Channels -> Channel Listing*).

### Endpoint elegido: Pay By Link

`POST /v1.02/paybylink/create` - crea una pagina hosted de Eupago donde el
cliente elige metodo (Multibanco, MB WAY, tarjeta, ...). Es el que encaja con
`create_checkout` porque devuelve una `checkout_url`.

Request (esenciales):

```json
{
  "payment": {
    "identifier": "<referencia unica nuestra>",
    "amount": {"value": 15.0, "currency": "EUR"},
    "successUrl": "<recharge_result>",
    "failUrl": "<recharge_result>",
    "backUrl": "<recharge_result>",
    "lang": "ES"
  },
  "customer": {"notify": false}
}
```

Response:

```json
{
  "transactionStatus": "Success",
  "transactionID": "af3df607c6724870be962a69cac30b99",
  "status": "Pendente",
  "redirectUrl": "https://sandbox.eupago.pt/api/extern/paybylink/form/..."
}
```

Errores: `transactionStatus: "Rejected"` con `code`/`text` (p. ej.
`APIKEY_MISSING`). Tratar cualquier cosa distinta de `Success` como fallo del
checkout (lanzar excepcion; `recharge_start` ya muestra mensaje de error).

### Webhook 2.0

- Metodo: **POST** con body **JSON** (el `dummy` usa `request.POST`; el
  gateway real debe leer `json.loads(request.body)`).
- Firma: header **`X-Signature`** = HMAC SHA-256 del body crudo con la
  *webhook key* de Eupago, en binario y despues base64. Verificacion estilo
  (de la doc oficial, traducida a Python):

  ```python
  import base64, hashlib, hmac
  expected = base64.b64encode(
      hmac.new(secret.encode(), request.body, hashlib.sha256).digest()
  )
  hmac.compare_digest(expected, signature.encode())
  ```

- Body: `{"transaction": {...}, "channel": {...}}` (verificado; la doc y el
  ejemplo PHP dicen `transactions` en plural). El parser localiza el bloque
  con `_extract_transaction`, que acepta `transaction`/`transactions` como
  objeto o como lista. Campos utiles:

  | Campo | Tipo | Uso en el proyecto |
  | ----- | ---- | ------------------- |
  | `identifier` | string | **Lo que nosotros enviamos al crear** => es el `gateway_order_id` para localizar la orden |
  | `status` | string | `Paid`, `Refund`, `Error`, `Cancel`, `Expired` |
  | `amount` | object | `{value, currency}` => se pasa a `confirm_payment` como validacion |
  | `trid` | integer | ID interno de Eupago (informativo, va al log) |
  | `method` | string | Multibanco/Mbway/CreditCard/... (informativo) |

  **Ojo:** el webhook **no** incluye `transactionID` (el hex que devuelve el
  create; en el aviso real aparece dentro de `transaction` pero no se usa).
  Por eso la referencia que viaja de ida y vuelta es `identifier`.

- Respuesta: debe devolver **HTTP 200** si no se quiere que Eupago reintente
  (reintentos: cada 2 min x3, luego cada hora durante 24 h). La vista
  `payment_webhook` ya devuelve `JsonResponse 200` en el caso de exito.
- Estados configurables en el backoffice al crear el webhook:
  `PAID`, `REFUNDED`, `ERROR`, `CANCELED`, `EXPIRED`.

## Decisiones de diseno (ya tomadas, seguir estas)

1. **Metodo: Pay By Link.** Es el unico que devuelve una URL de checkout
   hosted generica (el resto - Multibanco, MB WAY - requieren que el propio
   sitio muestre referencia/telefono y encajan peor con el contrato actual).
   Multibanco/MB WAY quedan igualmente disponibles *dentro* de la pagina de
   Eupago sin codigo extra.
2. **`identifier` como `gateway_order_id`.** `create_checkout` envia
   `identifier = f'recharge-{uuid4().hex}'` y devuelve ese mismo valor como
   `gateway_order_id` (se guarda en `RechargeOrder.gateway_order_id`). El
   webhook devuelve `transactions.identifier` y `parse_event` lo reentrega
   como `gateway_order_id`, con lo que `get_order_by_gateway_ref` lo
   localiza sin tocar modelos. El `transactionID` de Eupago se registra con
   `logger.info` (queda en `WebhookLog` al llegar el webhook).
3. **Mapeo de estados:**

   | Eupago `status` | Evento interno |
   | --------------- | -------------- |
   | `Paid` | `payment.succeeded` |
   | `Error` | `payment.failed` |
   | `Cancel` | `payment.failed` |
   | `Expired` | `payment.failed` |
   | `Refund` | **no configurar** en el webhook (ver punto 4) |

4. **Refunds fuera del alcance v1.** `services.refund_order` es un stub y la
   politica de reembolso esta pendiente en el roadmap. Al crear el webhook en
   el backoffice de Eupago **desmarcar `REFUNDED`** para no recibir eventos
   que la vista no soporta (devolveria 400 y provocaria reintentos 24 h).
5. **Sin dependencias nuevas.** `requests` ya esta en `requirements/base.txt`.
   Existe un SDK no oficial (`pip install eupago`, Python 3.9-3.13,
   production-validated) pero **no hace falta**: el flujo completo son dos
   llamadas HTTP. Si se prefiriera, seria opcional y habriara que evaluarlo.
6. **Modo por `AHHH_PAYMENT_MODE`**, no variable nueva: `test` =>
   `sandbox.eupago.pt`, `live` => `clientes.eupago.pt`.

## Plan de pasos

### Fase 0 - Comercial y credenciales (BLOQUEANTE, no es codigo)

- [x] **Confirmar con Eupago (soporte/ventas: suporte@eupago.pt) que aceptan
      contenido adulto legal, solo mayores.** Si la respuesta es no, parar aqui.
      (Hecho: la dueña del proyecto tiene el visto bueno de la plataforma.)
- [ ] Abrir cuenta en eupago.pt y completar la verificacion (KYC).
- [ ] Crear un canal en el backoffice y obtener la **API Key**
      (*Channels -> Channel Listing*).
- [ ] Obtener la **webhook key** (secreto de firma) y el detalle de configuracion
      del callback en el backoffice.
- [ ] Decidir metodos de pago a habilitar (Multibanco + MB WAY + tarjeta es lo
      habitual).

### Fase 1 - Codigo

- [x] **1. Crear `apps/payments/gateways/eupago.py`** con
      `class EupagoGateway(BaseGateway)`:

      - `name = 'eupago'`
      - `create_checkout(order)`:
        - leer de settings: `AHHH_EUPAGO_API_KEY`, `AHHH_PAYMENT_MODE`,
          `AHHH_PUBLIC_BASE_URL` (o `services.public_webhook_url()` para las
          URLs de retorno; `successUrl`/`failUrl`/`backUrl` apuntando a
          `reverse('payments:recharge_result', args=[order.id])` - construir
          la absoluta con el mismo helper/base URL).
        - `POST {base}/v1.02/paybylink/create` con `requests`, header
          `Authorization: ApiKey ...`, timeout razonable (10 s),
          `payment.identifier = f'recharge-{uuid4().hex}'`,
          `amount.value = float(order.amount_eur)`, `currency = order.currency`.
        - devolver `{'checkout_url': data['redirectUrl'],
          'gateway_order_id': identifier}`; si `transactionStatus != 'Success'`
          o falla la peticion, lanzar excepcion (la vista ya gestiona el
          error).
      - `verify_webhook(request)`:
        - leer header `X-Signature`, calcular HMAC SHA-256 de
          `request.body` con `AHHH_EUPAGO_WEBHOOK_SECRET` y comparar con
          `hmac.compare_digest` (ver snippet arriba). `False` si falta alguno.
      - `parse_event(request)`:
        - `json.loads(request.body)`; localizar el bloque de transaccion
          (`transaction` o `transactions`, objeto o lista).
        - mapear estado segun la tabla de decisiones.
        - devolver `{'event_type', 'gateway_order_id': identifier,
          'amount': amount['value'], 'currency': amount['currency'],
          'raw': body completo}`.
        - ante un payload sin la estructura esperada, lanzar excepcion (la
          vista ya responde 400).

      Hecho (oct. 2026). Detalles de la implementacion real:

      - helper local `_absolute_url(path)` con `AHHH_PUBLIC_BASE_URL` en lugar
        de importar `services` (evitaria el circular services -> gateways).
      - Sin `AHHH_EUPAGO_API_KEY` => `ImproperlyConfigured`; error de red/JSON
        o `transactionStatus != 'Success'` => `ValueError` con mensaje amable
        (que `recharge_start` muestra al usuario) y el detalle tecnico en el
        log. El `transactionID` del create se registra con `logger.info`.
      - `parse_event` localiza el bloque con `_extract_transaction` (acepta
        `transaction` singular -lo que envia Eupago-, `transactions` plural y
        lista), exige `identifier` + `status` mapeable y, en `Paid`, tambien
        `amount` (para no saltarse la validacion de importe de
        `confirm_payment`); el resto de statuses recibidos con importe se
        pasan tal cual. Cualquier payload inesperado => excepcion (400).
      - Verificado con smoke manual de los tres metodos + `manage.py check` +
        suite completa en verde (102 tests). Los tests formales quedan para la
        fase 2.
- [x] **2. Registrar** en `_GATEWAYS` de
      `apps/payments/gateways/registry.py`:
      `'eupago': EupagoGateway` (import correspondiente).
- [x] **3. Variables de entorno** en `.env.example` (solo comentarios, sin
      claves reales), siguiendo el patron existente:

      ```ini
      # AHHH_PAYMENT_GATEWAY=eupago
      # AHHH_PAYMENT_MODE=test
      # AHHH_EUPAGO_API_KEY=
      # AHHH_EUPAGO_WEBHOOK_SECRET=
      ```

      Y en `core/settings.py` (junto a `AHHH_PAYMENT_GATEWAY`, linea ~124,
      donde ya se leen con `os.getenv`) mapearlas a
      `settings.AHHH_EUPAGO_API_KEY` / `settings.AHHH_EUPAGO_WEBHOOK_SECRET`
      igual que el resto de variables de pago.

      Hecho (oct. 2026): registrada en `_GATEWAYS`, variables comentadas en
      `.env.example` (junto al ejemplo de stripe) y mapeadas en
      `core/settings.py` con defecto vacio (sin claves, `create_checkout`
      falla con `ImproperlyConfigured` y `verify_webhook` devuelve `False`).
      Verificado: `manage.py check` con `AHHH_PAYMENT_GATEWAY=eupago` resuelve
      el gateway y la suite completa sigue en verde (102 tests).

### Fase 2 - Tests

- [x] Anadir `EupagoGatewayTest` (o similar) en `apps/payments/tests.py`:
  - `create_checkout` devuelve `checkout_url` y `gateway_order_id` coherentes
    (mockear `requests.post` con `unittest.mock.patch`; no hay que golpear la
    red en tests).
  - Firma valida => `verify_webhook` True; firma ausente o incorrecta => False.
  - `parse_event` con payloads Paid/Error/Cancel/Expired => eventos esperados.
  - Webhook completo end-to-end (reuse de la idea de `RechargeFlowTest`):
    payload JSON firmado => orden PAID y saldo acreditado una sola vez.
- [x] Ejecutar la suite completa: `python manage.py test` (debe seguir
      pasando todo lo existente).

      Hecho (oct. 2026): `EupagoGatewayTest` con 21 tests en
      `apps/payments/tests.py`. Cobertura extra mas alla de lo listado:
      host de produccion en modo `live`, rechazos de Eupago (Rejected / sin
      redirectUrl / error de red) => `ValueError`, sin API key =>
      `ImproperlyConfigured`, `start_checkout` persistiendo la referencia,
      webhook con firma invalida / importe incorrecto / referencia
      desconocida => 400 sin acreditar, y `status=Error` => orden FAILED.
      Suite completa: **123 tests en verde** (102 previos + 21 nuevos).

      Ampliacion (oct. 2026): soporte del **webhook 1.0** (respaldo, sin
      secreto aparte). `verify_webhook` con GET valida `chave_api` contra
      `AHHH_EUPAGO_API_KEY` (comparacion con `hmac.compare_digest`);
      `parse_event` construye el evento desde los parametros (`identificador`,
      `valor`, `transacao`, `mp`...), exige ambos y convierte el importe a
      `Decimal` (acepta coma). `payment_webhook` acepta ahora GET y POST
      (`require_http_methods`). 13 tests nuevos (34 en la clase;
      **136 en la suite**).

      Verificado end-to-end en local (oct. 2026) con
      `maintenance/send_test_webhook.py`: un POST 2.0 firmado y un GET 1.0 con
      `chave_api` devolvieron **200**, la orden paso a PAID y el saldo se
      acredito (se revirtieron las ordenes de prueba). El endpoint real
      `https://ahibiza.com/pagos/webhook/` responde **405 a GET** (produccion
      aun tiene el codigo anterior, sin soporte 1.0) y **400 a POST** (pasarela
      no activada alli): falta desplegar en la fase 4.

### Fase 3 - Pruebas en sandbox (E2E manual)

- [ ] `.env` local: `AHHH_PAYMENT_GATEWAY=eupago`, `AHHH_PAYMENT_MODE=test`,
      API key de sandbox. La API key de produccion **no** sirve en sandbox (y
      viceversa); comprobar la que toca con
      `venv\Scripts\python.exe maintenance\check_eupago_apikey.py` (`--prod`
      para produccion, `--both` para ambas).
- [ ] Elegir version de webhook en el canal del backoffice. Si no se puede
      obtener la clave del canal ("Chave Criptografica"), configurar el
      **webhook 1.0** (GET): no necesita secreto, basta con que `chave_api`
      coincida con la API key. Limitacion: la 1.0 solo avisa de pagos
      realizados (no de error/cancelado/expirado), asi que las ordenes que no
      se pagan quedan PENDING hasta cancelarlas a mano.
- [ ] Si se usa 2.0: exponer el webhook a Eupago con un tunel HTTPS
      (p. ej. ngrok/cloudflared) apuntando a `/pagos/webhook/`; la URL a
      configurar en el backoffice es `public_webhook_url()`.
- [ ] Configurar el webhook en el backoffice de sandbox: URL, metodo POST
      (2.0) o GET (1.0), estados `PAID/ERROR/CANCELED/EXPIRED` en 2.0 (sin
      `REFUNDED`), sin cifrado AES (mantener el payload en JSON plano).
- [ ] Comprar un paquete con el metodo de prueba Multibanco y MB WAY, comprobar
      en `/control/` (o admin) que la orden pasa a PAID, que el saldo sube y
      que `Transaction` se crea.

      Sin credenciales de sandbox se puede ensayar el endpoint en local:
      crear una orden PENDING y lanzar
      `venv\Scripts\python.exe maintenance\send_test_webhook.py --identifier <gateway_order_id> --amount <importe>`
      (`--version 1.0` para el GET). Con el servidor levantado y
      `AHHH_PAYMENT_GATEWAY=eupago` + `AHHH_EUPAGO_WEBHOOK_SECRET` en el `.env`.
- [ ] Probar tambien el caso de fallo/expiracion y la recarga de la pagina
      (idempotencia: no duplicar saldo).

### Fase 4 - Produccion

- [ ] Cuenta Eupago en vivo, API key de produccion y webhook secret reales en
      el `.env` del servidor (nunca en el repo).
- [ ] `AHHH_PAYMENT_GATEWAY=eupago`, `AHHH_PAYMENT_MODE=live`.
- [ ] `AHHH_PUBLIC_BASE_URL=https://ahibiza.com` (o `www.ahibiza.com` segun
      dominio canonico; ver `docs/despliegue.md`) y webhook configurado en el
      backoffice de produccion apuntando a
      `https://<dominio>/pagos/webhook/`.
- [ ] Compra real minima (el paquete mas barato) y verificacion end-to-end.
- [ ] Actualizar `docs/pagos_pasarela.md` (seccion "Pendiente antes de cobrar
      de verdad" y "Estado") y `docs/state_of_play.md`/`docs/todo.md`.

## Riesgos y puntos abiertos

1. **Contenido adulto (bloqueante).** Pendiente de confirmar con Eupago
   (fase 0). Las condiciones publicas de Eupago no lo aclaran; es el motivo
   por el que el proyecto esta en `disabled`.
2. **HTTPS obligatorio** para el webhook: ya resuelto en produccion
   (`ahibiza.com` con Let's Encrypt); en local hace falta tunel.
3. **Reembolsos:** fuera de alcance v1 (no configurar `REFUNDED` en el
   webhook). La politica sigue pendiente en el roadmap.
4. **Expiration de Pay By Link:** por defecto el link caduca en 24 h; si el
   cliente no llega a pagar, la orden se queda PENDING (ya hay accion de
   cancelacion manual y el estado `Expired` del webhook la marcaria FAILED).
5. **Importes:** `confirm_payment` exige que `amount.value` del webhook
   coincida con `order.amount_eur` (comparacion Decimal, `15.0 == 15.00`); el
   proyecto solo opera en EUR, igual que Eupago.
6. **Cambios en la API de Eupago:** este documento refleja la API v1.02 y los
   webhooks 1.0/2.0 consultados en octubre 2026; si algo no cuadra al
   implementar, revisar el indice oficial (`eupago.readme.io/llms.txt`).
7. **Webhook 1.0 elegido como respaldo:** si no se consigue la clave del canal
   para la 2.0, se puede usar la 1.0 (solo requiere la API key). A cambio:
   no hay aviso de error/cancelado/expirado (ordenes PENDING hasta cancelar a
   mano) y la API key viaja en la query string.
8. **PayByLink:** confirmado operativo en el canal de produccion (la key creo
   un link). Si en algun canal no esta habilitado, el `create` devolvera
   `Rejected`; alternativas con redirect: Credit Card
   (`/v1.02/creditcard/create`) o MB WAY (requiere telefono del cliente).

## Checklist final de "listo para cobrar"

- [ ] Fase 0 completada (aceptacion de contenido adulto + credenciales).
- [ ] `eupago.py` creado, registrado y con tests verdes.
- [ ] Webhook con firma verificada funcionando en sandbox end-to-end.
- [ ] `.env` de produccion con claves reales (no en repo).
- [ ] Webhook de produccion en HTTPS devolviendo 200.
- [ ] Compra real de verificacion.
- [ ] Documentacion del proyecto actualizada (`pagos_pasarela.md`, `state_of_play.md`, `todo.md`).
