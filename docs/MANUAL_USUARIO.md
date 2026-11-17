# Manual de usuario — Atención al Paciente

Guía paso a paso de cada pantalla de la consola del Centro Médico San Bernardino. Está escrita para
el personal de las áreas que la usa a diario, sobre todo en tableta.

> **Qué es y qué no es.** La consola sirve para atender mejor al paciente: registrar sus
> requerimientos, pasarlos entre áreas, responderle por WhatsApp y medir cómo se atiende. **No** es
> un sistema clínico: no guarda diagnósticos ni historias médicas, y **no** gestiona citas.

## Contenido

1. [Antes de empezar](#1-antes-de-empezar)
2. [Casos](#2-casos)
3. [Detalle de un caso](#3-detalle-de-un-caso)
4. [Tareas de un caso](#4-tareas-de-un-caso)
5. [Pacientes](#5-pacientes)
6. [Conversaciones (WhatsApp)](#6-conversaciones-whatsapp)
7. [Notificaciones](#7-notificaciones)
8. [Paneles](#8-paneles)
9. [Informes](#9-informes)
10. [Usuarios](#10-usuarios-solo-administradores)
11. [Mi cuenta](#11-mi-cuenta)
12. [Problemas frecuentes](#12-problemas-frecuentes)
13. [Glosario](#13-glosario)

---

## 1. Antes de empezar

### 1.1 Los cuatro conceptos

| Concepto | Qué es |
|---|---|
| **Paciente** | La persona atendida. Se registra una sola vez, con nombre, apellido, cédula, teléfono y correo. |
| **Caso** | Un requerimiento del paciente que una o varias áreas deben resolver. Ejemplo: «Resultados retrasados». Puede nacer en la sala o desde un chat. |
| **Conversación** | El chat de WhatsApp con el paciente. Un caso y una conversación son cosas distintas: un caso puede tener chat o no, y cerrar uno no cierra el otro. |
| **Tarea** | Un contacto con el paciente que alguien debe hacer: **Llamar**, **WhatsApp** o **Correo**. Se asigna a una persona, de cualquier área. |

### 1.2 Cada persona usa su cuenta

Cada persona tiene su propia cuenta y todo lo que hace queda registrado **a su nombre**: quién creó
un caso, quién cambió su etapa, quién completó una tarea. Por eso:

- **No comparta su cuenta** ni su contraseña, aunque la tableta sea del área.
- **Cierre sesión al terminar.** Si deja la sesión abierta, lo que haga la siguiente persona quedará a su nombre.
- Su nombre aparece siempre abajo en el menú lateral, para saber con qué cuenta se está trabajando.

### 1.3 Entrar y salir

1. Abra la dirección de la consola en el navegador.
2. Escriba su **correo** y su **contraseña**.
3. Pulse **Entrar**. Llegará a la pantalla **Casos**.
4. Para salir, pulse el icono de salida (abajo en el menú lateral) o **Salir**.

Si olvidó su contraseña, pídale a un administrador que la restablezca (ver [Usuarios](#10-usuarios-solo-administradores)).
Después puede cambiarla usted en [Mi cuenta](#11-mi-cuenta).

### 1.4 Roles: qué ve cada persona

| Rol | Qué puede hacer |
|---|---|
| **Agente** | Casos, pacientes y tareas (todas las áreas se ven entre sí). En conversaciones, la cola de su área y sus propios chats. |
| **Supervisor** | Lo del agente, más **todas** las conversaciones (incluidas las del bot), **Paneles** e **Informes**. |
| **Administrador** | Lo del supervisor, más **Usuarios** y los catálogos del centro. |

### 1.5 El menú lateral

Está a la izquierda (en el teléfono, abajo). Cada sección es un icono con su nombre.

| Sección | Para qué sirve | Quién la ve |
|---|---|---|
| **Casos** | Gestionar requerimientos entre áreas y ver la sala | Todos |
| **Conversaciones** | Atender los chats de WhatsApp | Todos |
| **Pacientes** | Registrar y buscar pacientes | Todos |
| **Paneles** | Ver indicadores | Supervisor y administrador |
| **Informes** | Descargar tablas en CSV | Supervisor y administrador |
| **Usuarios** | Crear y gestionar cuentas | Administrador |

Los **globos** sobre los iconos son avisos rápidos:

- En **Casos**: cuántos casos están por atender (*Registrado*). Se pone **rojo** si alguno está fuera de la meta.
- En **Conversaciones**: cuántos chats están en cola. Se pone **rojo** si alguno es urgente.

En la parte baja del menú está su **nombre**. Al pulsarlo se abre [Mi cuenta](#11-mi-cuenta).

### 1.6 Consejos para la tableta

- Todos los botones están pensados para el dedo: son grandes y hacen un solo trabajo.
- Los filtros son «píldoras»: pulse una para activarla (queda en negro).
- Las listas se actualizan solas cada pocos segundos. No hace falta recargar la página.

---

## 2. Casos

Es la pantalla principal: aquí se ve y se gestiona todo lo que está pendiente entre áreas.

### 2.1 Qué se ve, de arriba abajo

1. **Encabezado.** El título, la **campana** de [notificaciones](#7-notificaciones) y el botón **Nuevo caso**.
2. **Mis tareas pendientes.** Solo aparece si usted tiene tareas asignadas. Cada una dice qué hacer y a quién (*«Llamar a María Pérez»*). Al tocarla se abre su caso.
3. **Sala ahora.** La situación en tiempo real (ver [2.2](#22-la-sala-ahora)).
4. **Tarjetas por área.** Una por cada área, con cuántos casos tiene por atender, en atención y en espera. El número rojo indica casos fuera de la meta.
5. **Filtros** y **buscador**.
6. **Tabla de casos.**

### 2.2 La sala ahora

Es la tarjeta negra. Muestra, en este momento:

| Dato | Qué significa |
|---|---|
| **Registrado** | Casos creados que nadie ha empezado a atender |
| **En atención** | Casos que alguien está atendiendo |
| **En espera** | Casos detenidos (por ejemplo, esperando un resultado) |
| **Resuelto** | Casos solucionados que falta cerrar |
| **Fuera de meta** | Casos *Registrados* que llevan más tiempo esperando que la meta (15 minutos) |
| **Espera más larga** | Cuánto lleva el caso *Registrado* más antiguo sin atenderse |

Arriba a la derecha hay un resumen del día: casos creados, cerrados, tiempo mediano hasta la primera
atención y tiempo mediano de resolución.

**Tocar una etapa** (por ejemplo *Registrado*) filtra la tabla de abajo a esos casos. Vuelva a tocarla para quitar el filtro.
**Tocar una tarjeta de área** filtra por esa área; vuelva a tocarla para quitarlo.

### 2.3 Filtrar y buscar casos

1. Elija una etapa en las píldoras: **Abiertos** (todo lo que no está cerrado), **Registrado**, **En atención**, **En espera**, **Resuelto** o **Cerrados**.
2. Pulse **Mis casos** para ver solo los que usted tiene a cargo.
3. Elija un área en **Todas las áreas**.
4. Escriba en el buscador: puede buscar por **asunto**, por **nombre del paciente**, por **cédula** o por el **número del caso** (por ejemplo `#14`).

La tabla muestra las primeras 50 coincidencias; si hay más, use los filtros o el buscador para acotar.

### 2.4 Leer la tabla

| Columna | Qué dice |
|---|---|
| **Caso** | El asunto y su número |
| **Paciente** | Nombre y cédula |
| **Área y responsable** | El área que lo tiene y quién lo atiende (*Sin asignar* si nadie) |
| **Etapa** | Su etapa; **Urgente** en rojo si tiene prioridad alta |
| **En etapa** | Cuánto lleva en esa etapa. En un caso *Registrado* el color avisa: verde (va bien), ámbar (se acerca a la meta), rojo (pasó la meta) |

Los casos urgentes salen primero. Toque cualquier fila para abrir el caso.

### 2.5 Crear un caso nuevo

1. Pulse **Nuevo caso**.
2. En **Paciente**, escriba el nombre, la cédula o el teléfono. Toque al paciente en la lista.
3. Si el paciente **no está registrado**, pulse **Registrar paciente nuevo**, complete sus cinco datos (ver [Pacientes](#5-pacientes)) y siga. Se registrará junto con el caso.
4. Escriba el **Asunto** (mínimo 3 letras). Es obligatorio.
5. Elija el **Área responsable**. Viene sugerida su propia área.
6. Opcional: una **Descripción** y la **Prioridad** (*Normal* o *Urgente*).
7. Pulse **Crear caso**. Se abre el caso recién creado, en etapa **Registrado**.

> También puede crear un caso desde la ficha de un paciente (botón **Nuevo caso**) o desde un chat
> (ver [6.9](#69-crear-un-caso-desde-un-chat)).

---

## 3. Detalle de un caso

Se abre al tocar un caso en cualquier lista.

### 3.1 Qué se ve

- **Arriba:** número, asunto y los botones **Tomar caso**, **Asignar**, **Transferir** y **Editar**.
- **Datos clave:** paciente, área, responsable, cuándo se abrió y el origen (*Presencial* o *WhatsApp*).
- **La barra de etapas.** Muestra por dónde va el caso. La etapa actual está en negro, las anteriores con una marca ✓. *En espera* se muestra apagada si el caso nunca pasó por ahí. A su derecha están los botones para avanzar.
- **Pestañas:** **Detalles**, **Notas** y **Actividad**.
- **A la derecha:** el paciente (toque para abrir su ficha), las **Tareas** y, si el caso nació de un chat, un botón **Abrir chat**.

### 3.2 Las etapas

Un caso recorre estas etapas:

> **Registrado** → **En atención** → *(En espera)* → **Resuelto** → **Cerrado**

| Etapa | Cuándo |
|---|---|
| **Registrado** | El caso se creó y nadie lo ha empezado |
| **En atención** | Alguien lo está atendiendo |
| **En espera** | Está detenido: se espera al paciente, un resultado u otra persona. Es opcional |
| **Resuelto** | El requerimiento quedó solucionado |
| **Cerrado** | Se cerró con su motivo. Es el final |

### 3.3 Cambiar de etapa

Los botones a la derecha de la barra cambian según la etapa. Solo aparecen los pasos permitidos:

| Está en… | Botones |
|---|---|
| Registrado | **Iniciar atención** |
| En atención | **Marcar como resuelto**, **Poner en espera** |
| En espera | **Reanudar atención** |
| Resuelto | **Cerrar caso**, **Volver a atención** |
| Cerrado | **Reabrir caso** |

**Paso a paso para atender un caso:**

1. Abra el caso y pulse **Iniciar atención**. Si nadie lo tenía a cargo, usted queda como responsable.
2. Si debe esperar algo, pulse **Poner en espera** y luego **Reanudar atención** cuando pueda seguir.
3. Al terminar, pulse **Marcar como resuelto**.
4. Pulse **Cerrar caso**, elija el **Motivo de contacto** (es obligatorio: alimenta los indicadores) y confirme.

**Para cerrar** el caso no debe tener **tareas pendientes**: complételas o cancélelas antes (ver [4](#4-tareas-de-un-caso)).
Un caso *Resuelto* sí puede tener tareas pendientes.

> Cambiar la etapa **no** le envía ningún mensaje al paciente ni cierra su chat.

### 3.4 Tomar, asignar y transferir

- **Tomar caso:** usted queda como responsable. Solo aparece si el caso no es suyo.
- **Asignar:** ponga el caso a cargo de **otra persona**, de cualquier área.
  1. Pulse **Asignar**.
  2. Elija a la persona en **Asignar a** (están agrupadas por área).
  3. Pulse **Asignar**. La persona recibe una [notificación](#7-notificaciones).
- **Transferir:** pase el caso a **otra área**.
  1. Pulse **Transferir** y elija el **Área**.
  2. El caso vuelve a **Registrado** y **sin responsable** en la nueva área, que debe tomarlo.
  3. No se puede transferir un caso *Resuelto* o *Cerrado*.

Cada área responde por el tiempo que el caso pasó con ella.

### 3.5 Editar

Pulse **Editar** para cambiar el asunto, la descripción o la prioridad. Un caso cerrado no se edita: reábralo primero.

### 3.6 Notas y actividad

- **Notas.** Para dejar comentarios al equipo. Escriba en el recuadro y pulse el botón de enviar. La más reciente sale primero y cada una lleva su autor y su hora. Son internas: el paciente no las ve.
- **Actividad.** El historial completo: creación, cambios de etapa, asignaciones, transferencias, tareas y notas, cada uno con quién lo hizo y cuándo.

> Escriba las notas con criterio: son datos de salud del paciente y las ve todo el personal que tenga acceso a la consola.

---

## 4. Tareas de un caso

Una tarea es un contacto con el paciente que alguien debe hacer. Sirve para dar seguimiento personalizado
y para pedirle algo a otra persona, aunque sea de otra área.

> Una tarea es un **recordatorio**. Completarla **no envía nada** al paciente: la persona hace la
> llamada, escribe el WhatsApp o envía el correo por su cuenta y luego la marca como hecha.

### 4.1 Crear una tarea

1. Abra el caso. A la derecha, en la tarjeta **Tareas**, pulse **Nueva**.
2. Elija el tipo: **Llamar**, **WhatsApp** o **Correo**.
3. En **Asignar a**, elija a la persona (puede ser usted).
4. Opcional: la **Prioridad** (*Urgente* la destaca) y las **Indicaciones**, por ejemplo *«Confirmar que recibió los resultados»*.
5. Pulse **Crear tarea**. La persona recibe una [notificación](#7-notificaciones).

No se pueden crear tareas en un caso cerrado.

### 4.2 Hacer una tarea

1. Entre por **Mis tareas pendientes** (en Casos) o por la notificación. Se abre el caso.
2. En la tarjeta **Tareas** verá la suya, marcada **Para usted**, con sus indicaciones.
3. Use el acceso directo para contactar al paciente:
   - **Llamar:** el teléfono del paciente. En un teléfono o tableta, al tocarlo se inicia la llamada.
   - **Correo:** su correo. Al tocarlo se abre su programa de correo.
   - **WhatsApp:** abre el chat si el caso nació de una conversación y usted puede verla; si no, muestra el número.
4. Cuando termine, pulse **Completar**.
5. Si ya no hace falta, pulse **Cancelar** y confirme con **Sí, cancelar**.

Las tareas terminadas quedan debajo como constancia: *«Completada por Ana · 12:08 p. m.»*. Cualquier persona
puede completar o cancelar una tarea; queda registrado quién lo hizo.

---

## 5. Pacientes

Aquí se registran y se buscan los pacientes. Todas las áreas ven a todos los pacientes.

### 5.1 Registrar un paciente

1. Pulse **Nuevo paciente**.
2. Complete los **cinco datos**; todos son obligatorios. Los campos vacíos se marcan en rojo al guardar.

| Dato | Cómo escribirlo |
|---|---|
| **Nombre** y **Apellido** | Como figuran en su documento |
| **Cédula de identidad** | `V-12345678`. Puede llevar puntos o guiones; el sistema los normaliza. **No puede repetirse** |
| **Teléfono** | `4141234567`, sin el 0 inicial ni `+58`. También se acepta `0414-1234567` y `+58 414 123 4567`. Un número extranjero se escribe con su código de país (`+57 300 123 4567`) |
| **Correo** | `nombre@dominio.com` |

3. Pulse **Guardar**. Se abre la ficha del paciente.

Si la cédula ya existe, el sistema avisa *«Ya existe un paciente con esa cédula»*: búsquelo en vez de crearlo de nuevo.

### 5.2 Buscar un paciente

Escriba en el buscador de la pantalla **Pacientes**: nombre, apellido, cédula, teléfono o correo. Puede
escribir varias palabras (*«maría pérez»*). Toque una fila para abrir la ficha.

### 5.3 La ficha del paciente

- **Datos:** cédula, teléfono, correo y cuándo se registró.
- **Editar:** corrija cualquier dato. Se aplican las mismas reglas.
- **Nuevo caso:** crea un caso para este paciente.
- **Casos:** todos sus casos, con su etapa. Toque uno para abrirlo.
- **Historial de la ficha:** quién la registró, quién la editó (y qué campos, sin mostrar los valores) y cuándo se vinculó a su WhatsApp.

---

## 6. Conversaciones (WhatsApp)

Aquí se atienden los chats con los pacientes. Primero responde un **bot**; cuando hace falta una persona,
el chat pasa a la **cola** de un área.

### 6.1 Cómo llega un chat

1. El paciente escribe al WhatsApp del centro.
2. El **bot** lo saluda y le muestra un menú numerado con las áreas y las **Preguntas frecuentes**.
3. El paciente elige un número. Según lo que elija, el bot responde con la información o **lo deriva a un agente** del área.
4. El chat queda **En cola** hasta que un agente lo acepte.
5. Si el mensaje parece una **urgencia**, el chat se marca **Urgente**, el paciente recibe el mensaje de Emergencia y el chat pasa a la cola con prioridad.

El bot nunca da diagnósticos ni recomienda medicamentos: solo informa con textos fijos y deriva.

### 6.2 La pantalla

- **Izquierda:** la lista de chats, con filtros: **Abiertas**, **Cola**, **Mías**, **En espera** y **Cerradas**. Los supervisores ven también **Bot**.
- **Centro:** el chat seleccionado.
- **Derecha:** el detalle del caso (en pantallas pequeñas, se abre con el botón **Detalle**).

Cada chat de la lista muestra el nombre, el último mensaje, su estado y, si está en cola, un reloj con el
tiempo de espera. El reloj se pone ámbar y luego rojo cuando se acerca a la meta del área.

### 6.3 Aceptar un chat

1. En **Cola**, toque un chat.
2. Pulse **Aceptar**. Queda **Abierta** y a su nombre.

Los supervisores pueden además **Intervenir** un chat que aún atiende el bot.

### 6.4 Responder al paciente

1. Con el chat aceptado, escriba en el recuadro **Responder**.
2. Pulse el botón de enviar, o **Ctrl + Enter**.

**Importante:** WhatsApp solo permite responder libremente durante **24 horas** desde el último mensaje del
paciente. Pasado ese tiempo, la consola avisa y solo se pueden enviar plantillas aprobadas.

### 6.5 Notas internas

Cambie a la pestaña **Nota interna** (candado) para dejar un comentario visible **solo para el equipo**.
Nunca se envía al paciente. Se distinguen por su fondo amarillo.

### 6.6 El copiloto (ayuda de redacción)

Junto al recuadro de respuesta hay dos botones de ayuda:

- **Sugerir:** propone una respuesta según la conversación.
- **Mejorar:** corrige y pule el texto que usted ya escribió.

En el detalle del caso, **Resumir** genera un resumen de la conversación para ponerse al día rápido.

> Las propuestas **nunca se envían solas**: revíselas y edítelas antes de enviar. Antes de pedirlas, los
> datos del paciente se anonimizan.

### 6.7 Acciones sobre el chat (panel derecho)

| Botón | Qué hace |
|---|---|
| **En espera** | Pausa el chat mientras espera al paciente. Cuando el paciente responde, se reanuda solo |
| **Reanudar** | Lo vuelve a abrir manualmente |
| **Transferir** | Lo pasa a la cola de otra área y deja de estar a su nombre |
| **Cerrar** | Termina el chat (ver 6.8) |
| **Reabrir** | Reabre un chat cerrado |

### 6.8 Cerrar un chat

1. Pulse **Cerrar**.
2. Elija el **Motivo de contacto**. Es obligatorio. Puede usar **Sugerir** para que el copiloto lo proponga.
3. Deje marcada **Enviar encuesta de satisfacción** si corresponde. El paciente la recibe por WhatsApp y califica la atención del 1 al 5.
4. Pulse **Cerrar caso**.

La encuesta **no se envía** si el chat fue una urgencia, o si el paciente ya recibió una en los últimos 30 días.
El diálogo lo avisa de antemano.

En el detalle del chat, **Acepta mensajes proactivos** registra el consentimiento del paciente para recibir
mensajes que no son respuesta, como la encuesta mensual. Márquelo **solo si el paciente lo autorizó expresamente**.

### 6.9 Crear un caso desde un chat

1. Con el chat abierto, pulse **Crear caso** (arriba, junto al nombre del paciente).
2. El sistema busca al paciente por su número de WhatsApp. Si ya está registrado, aparece elegido.
3. Si **no** está registrado, pulse **Registrar paciente nuevo**. El nombre y el teléfono vienen rellenos con los datos del chat: complete **la cédula** y **el correo** (pídaselos al paciente) y corrija el nombre si hace falta.
4. Escriba el **Asunto**, elija el **Área** (viene la del chat) y pulse **Crear caso**.

El caso queda vinculado al chat: lo verá en el panel **Casos** del chat, y el caso tendrá un botón **Abrir chat**.

### 6.10 El botón «Simular»

Solo existe en pruebas, no en producción. Permite inyectar un mensaje de un paciente ficticio para ver
cómo reacciona la consola. Lo ven supervisores y administradores.

---

## 7. Notificaciones

Avisan cuando alguien le **asigna una tarea** o un **caso**.

### 7.1 La campana

Está en el encabezado de cada pantalla, a la izquierda del botón de acción (por ejemplo, antes de
**Nuevo caso**). Si hay algo sin leer, aparece un **círculo rojo** sobre la campana.

Cuando llega una notificación nueva, además aparece un mensaje breve abajo a la derecha, aunque tenga el
panel cerrado. La campana se actualiza sola, sin recargar.

### 7.2 Usar el panel

1. Pulse la **campana**. Se abre un panel sobre la misma pantalla.
2. Las notificaciones sin leer van en **negrita**, con un punto. Cada una dice qué le asignaron, quién y cuándo, por ejemplo: *«Ana le asignó llamar a María Pérez · Caso #14»*.
3. **Toque una** para abrir el caso. Queda marcada como leída.
4. Pulse **Marcar todas como leídas** para limpiar el aviso.
5. Cierre el panel tocando fuera de él, con **Esc** o desplazando la página.

### 7.3 Qué debe saber

- No se le avisa de lo que usted mismo se asigna.
- El panel muestra las **30 más recientes**.
- Las notificaciones son **privadas**: nadie más puede verlas ni marcarlas.
- Si una tarea sigue pendiente, la seguirá viendo en **Mis tareas pendientes** de la pantalla Casos aunque ya haya leído el aviso.
- No hay aviso por sonido ni por correo: la persona se entera con la consola abierta.

---

## 8. Paneles

*Solo supervisores y administradores.* Muestran cómo va la atención.

### 8.1 Elegir qué ver

1. Arriba, elija **Casos** o **WhatsApp**. Se miden distinto y por eso van separados.
2. Elija el período: **Hoy**, **7 días**, **30 días** o **Este mes**.
3. Opcional: filtre por **área**.

El período y el área quedan en la dirección de la página: puede copiarla y compartirla.

### 8.2 Panel de Casos

| Indicador | Qué mide |
|---|---|
| **Tiempo hasta atender** | Desde que el caso entra a un área hasta que alguien inicia la atención (mediana y percentil 90) |
| **Meta cumplida** | Porcentaje de casos atendidos dentro de la meta (15 minutos), igual para todas las áreas |
| **Tiempo en atención** | Cuánto estuvo el caso en la etapa *En atención* |
| **Resolución** | Desde que se crea hasta que se resuelve, sin contar las esperas |
| **Casos creados / cerrados** | Cuántos hubo en el período, y cuántos son urgentes |
| **En espera** | Cuánto estuvieron detenidos los casos que pasaron por esa etapa |
| **Transferidos** | Porcentaje de casos que cambiaron de área, y cuántos se reabrieron |

Más abajo:

- **Motivos de cierre:** por qué se cerraron los casos.
- **Por área:** cada área responde solo por el tiempo que el caso estuvo con ella.
- **Por persona:** qué hizo cada quien con su cuenta: casos atendidos, tiempo en atención, resueltos, transferidos y cerrados.

### 8.3 Panel de WhatsApp

Arriba, la franja **Ahora** muestra el estado en tiempo real: casos en cola, urgentes, la espera más larga,
chats en el bot, abiertos y agentes conectados.

| Indicador | Qué mide |
|---|---|
| **Tiempo de 1ª respuesta** | Cuánto tarda un agente en responder al paciente por primera vez |
| **SLA cumplido** | Porcentaje de chats respondidos dentro de la meta del área |
| **CSAT** | Satisfacción del paciente, de 1 a 5, y cuántos quedaron satisfechos (4 o 5) |
| **NPS** | Qué tan probable es que el paciente recomiende al centro (de −100 a 100) |
| **Resolución** | Cuánto tarda en resolverse un chat y qué porcentaje se resuelve |
| **Resueltos al 1er contacto** | Chats resueltos sin transferencias ni reaperturas |
| **Abandono** | Chats en los que el paciente nunca recibió respuesta humana |
| **Resueltas por el bot** | Chats que el bot resolvió sin pasar a una persona |

También hay gráficos de mensajes por hora y CSAT por día, y tablas por área y por agente.

### 8.4 Cómo leer los tiempos

- Los tiempos del panel se miden en **minutos hábiles**: solo cuentan las horas de atención del área, sin feriados. Por eso un caso que entra por la noche empieza a contar al abrir.
- La tarjeta **Sala ahora** de la pantalla Casos usa **minutos de reloj**, porque quien espera en la sala espera igual fuera de horario. Por eso sus cifras pueden diferir de las del panel.
- Un valor **«—»** significa que todavía no hay datos suficientes para calcularlo.
- Las definiciones exactas de cada fórmula están en [METRICAS.md](METRICAS.md).

---

## 9. Informes

*Solo supervisores y administradores.* Son las mismas cifras, en tablas detalladas que se descargan.

1. Elija **Casos** o **WhatsApp**.
2. Elija el período y, si quiere, el área.
3. En cada tabla pulse **CSV** para descargarla. Se abre directamente en Excel, en español (separada por punto y coma y con coma decimal).

| Vista | Tablas |
|---|---|
| **Casos** | Por área, por persona y motivos de cierre |
| **WhatsApp** | Por área, por agente, por hora y motivos de contacto |

---

## 10. Usuarios (solo administradores)

Aquí se crean y se gestionan las cuentas. **Cada persona debe tener la suya.**

### 10.1 Crear un usuario

1. Pulse **Nuevo usuario**.
2. Escriba el **Nombre y apellido** y el **Correo** (será su usuario; no se puede cambiar después).
3. Elija su **Área** o deje **Sin área (todas)**.
4. Escriba una **Contraseña inicial** (mínimo 10 caracteres).
5. Elija el **Rol**: *Agente*, *Supervisor* o *Administrador*.
6. Pulse **Guardar**.
7. Entréguele la contraseña a la persona y pídale que la cambie en **Mi cuenta** en su primer ingreso.

### 10.2 Editar, restablecer o desactivar

- **Editar:** toque la fila. Puede cambiar nombre, área y rol.
- **Restablecer contraseña:** dentro de la edición, escriba una **Contraseña nueva** y guarde.
- **Desactivar:** pulse **Desactivar** en su fila. La persona ya no podrá entrar, pero lo que hizo se conserva con su nombre. **Activar** la restituye.

No puede cambiarse su propio rol ni desactivar su propia cuenta, para que el centro no se quede sin administrador.

La columna **Última actividad** muestra cuándo estuvo conectada cada persona.

---

## 11. Mi cuenta

1. Pulse su **nombre** (abajo en el menú lateral).
2. Verá sus datos: nombre, correo, rol y área.
3. Para cambiar la contraseña, escriba la **actual**, la **nueva** (mínimo 10 caracteres) y repítala.
4. Pulse **Guardar**.

Úsela solo usted. Todo lo que se haga con su cuenta se le atribuye.

---

## 12. Problemas frecuentes

| Qué pasa | Qué hacer |
|---|---|
| *«El caso cambió de etapa: revise su estado actual»* | Otra persona lo movió antes. La pantalla se actualiza sola: revise la etapa y vuelva a intentarlo si sigue haciendo falta |
| No puedo cerrar el caso | Debe elegir un motivo y no tener **tareas pendientes**. Complételas o cancélelas |
| No puedo transferir el caso | Solo se transfieren casos *Registrado*, *En atención* o *En espera*. Uno resuelto o cerrado no |
| No puedo editar, asignar ni crear tareas | El caso está **cerrado**. Pulse **Reabrir caso** |
| *«Ya existe un paciente con esa cédula»* | El paciente ya está registrado: búsquelo en **Pacientes** |
| *«Escríbalo así: 4141234567»* | El teléfono no tiene el formato correcto. Escriba 10 dígitos, sin el 0 inicial |
| No puedo responder en un chat | Primero **acepte** el caso, o pasaron más de 24 horas del último mensaje del paciente |
| No veo un chat de otra área | Los chats se ven por área. Los **casos** y los **pacientes**, en cambio, los ven todas las áreas |
| No veo Paneles, Informes o Usuarios | Son solo para supervisores y administradores. Pida el cambio de rol a un administrador |
| La campana tiene un círculo rojo pero no veo nada nuevo | Ábrala: puede haber una notificación sin leer más abajo. Use **Marcar todas como leídas** |
| La página no carga o dice «error 502» | Es un problema de conexión con el servidor. Espere un minuto y recargue; si persiste, avise a soporte |

---

## 13. Glosario

| Término | Significado |
|---|---|
| **Área** | Departamento del centro (Atención al paciente, Laboratorio, Imagenología…) |
| **Asignar** | Poner un caso o tarea a cargo de una persona |
| **Bot** | El asistente automático que atiende primero los chats de WhatsApp |
| **Campana** | El botón de notificaciones |
| **Caso** | Requerimiento de un paciente gestionado entre áreas |
| **Cola** | Chats que esperan a que un agente los acepte |
| **Copiloto** | La ayuda de redacción con inteligencia artificial (Sugerir, Mejorar, Resumir) |
| **CSAT** | Encuesta de satisfacción tras un chat (1 a 5) |
| **Fuera de meta** | Caso por atender que lleva más tiempo esperando que la meta |
| **Meta** | Tiempo máximo esperado hasta empezar a atender (15 minutos para casos) |
| **Minutos hábiles** | Minutos dentro del horario de atención, sin feriados |
| **NPS** | Encuesta periódica de recomendación (−100 a 100) |
| **SLA** | Cumplimiento de la meta de primera respuesta de un chat |
| **Tarea** | Contacto pendiente con el paciente: Llamar, WhatsApp o Correo |
| **Transferir** | Pasar un caso o chat a otra área |
