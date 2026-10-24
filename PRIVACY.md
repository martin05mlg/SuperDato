# Política de Privacidad y Protección de Datos (RGPD / GDPR)

**SuperDato** está diseñado bajo el principio de **privacidad por diseño** (*Privacy by Design*) y **soberanía del dato** (*Self-Hosted*).

## 1. Alojamiento y Control de los Datos
Cuando despliegas SuperDato en tu propio servidor o NAS mediante Docker:
- Todos los tickets, productos, métricas de gasto y credenciales se almacenan exclusivamente en tu base de datos PostgreSQL local.
- El proyecto **no incluye telemetría**, analítica de terceros ni envío de datos a servidores externos del autor.

## 2. Integración Opcional con Google Gmail (`gmail.readonly`)
Si decides vincular tu cuenta de Gmail:
- SuperDato solicita únicamente el permiso de lectura `https://www.googleapis.com/auth/gmail.readonly`.
- El sincronizador filtra exclusivamente correos que contengan adjuntos PDF de tickets digitales y nunca lee otros correos personales.
- Los tokens OAuth (`access_token` y `refresh_token`) se almacenan cifrados en reposo mediante **AES-256-GCM** utilizando la clave maestra (`ENCRYPTION_MASTER_KEY`) de tu instancia.

## 3. Derechos del Usuario (Acceso, Portabilidad y Supresión)
SuperDato incorpora endpoints nativos para cumplir con el Reglamento General de Protección de Datos (RGPD):
- **Derecho de Acceso y Portabilidad (Art. 15 y 20 RGPD)**: cualquier usuario autenticado puede descargar una exportación completa en formato JSON de su perfil, hogares, tickets y listas mediante `GET /api/v1/auth/me/export`.
- **Derecho de Supresión / Olvido (Art. 17 RGPD)**: cualquier usuario puede eliminar de forma irreversible su cuenta, sus vínculos OAuth y los hogares de los que sea único miembro mediante `POST /api/v1/auth/me/delete`.

