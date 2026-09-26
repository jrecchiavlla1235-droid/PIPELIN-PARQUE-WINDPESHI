# Sistema de Evaluación Energética y Factibilidad Eólica - Parque Windpeshi (Uribia, La Guajira)

Sistema integral de adquisición de datos climáticos, simulación termodinámica/aerodinámica y balance de factibilidad energética para cargas industriales en el municipio de **Uribia (La Guajira, Colombia)**.

---

## 1. Visión General del Proyecto

El Parque Eólico Windpeshi aprovecha los vientos Alisios del noreste en la península de La Guajira, una de las zonas con mayor densidad de potencia eólica del continente. 

Este repositorio implementa un **pipeline automatizado de datos y modelado físico** que responde a dos preguntas críticas de ingeniería:
1. **Recurso Eólico Diario:** ¿Son las condiciones meteorológicas de una jornada óptimas para la generación eólica según las zonas operativas de una turbina industrial?
2. **Factibilidad y Balance Industrial:** ¿Cuánta energía genera el sistema frente a la demanda horaria de una empresa consumidora, cuál es el porcentaje de cobertura, cuántas horas de autonomía continua brinda y qué capacidad de almacenamiento (BESS) o respaldo de red se necesita?

---

## 2. Arquitectura del Sistema

El software sigue una arquitectura modular con estricta **separación de responsabilidades (SoC)**:

```text
PIPELIN-PARQUE-WINDPESHI/
├── config/
│   └── settings.py          # Constantes termodinámicas, ubicación geográfica y especificaciones de turbina
├── data/
│   ├── cache/               # Almacenamiento local JSON de la API meteorológica (resiliencia DAQ)
│   └── processed/           # Series temporales exportadas en CSV con balances horarios
├── src/
│   ├── daq/
│   │   └── climate_api.py   # Ingesta de datos de Open-Meteo con caché y conversión horaria UTC-5
│   ├── domain/
│   │   ├── wind_physics.py  # Modelado termodinámico (ρ), extrapolación logarítmica y curva de potencia
│   │   └── demand_model.py  # Perfiles de demanda horaria para maquinaria industrial
│   ├── pipeline.py          # Orquestador del pipeline clásico de favorabilidad del parque
│   └── energy_balance.py    # Pipeline de balance energético diario, cobertura y autonomía
├── visualization/
│   └── energy_plots.py      # Generador de curvas 24h con Seaborn y Matplotlib (excedentes vs déficit)
├── reports/
│   └── *.png                # Gráficos generados en alta resolución (300 DPI)
├── main.py                  # CLI principal unificado
├── requirements.txt         # Dependencias científicas
└── README.md                # Documentación técnica del repositorio
```

---

## 3. Fundamentos de Física e Ingeniería

### 3.1. Densidad Real del Aire ($\rho$)
A diferencia de los modelos simplificados que asumen la densidad estándar de la atmósfera tipo ISA ($\rho_0 = 1.225\text{ kg/m}^3$), en Uribia la temperatura suele superar los $32\text{ °C}$. El sistema calcula hora a hora la densidad real usando la ecuación de los gases ideales:

$$\rho = \frac{P \cdot 100}{R_{aire} \cdot (T_{°C} + 273.15)}$$

Donde:
* $P$: Presión atmosférica en superficie (hPa).
* $R_{aire} = 287.058\text{ J/(kg}\cdot\text{K)}$ (constante para aire seco).
* $T_{°C}$: Temperatura ambiente a 2m.

### 3.2. Extrapolación del Viento por Ley Logarítmica de Prandtl
Las estaciones meteorológicas y satélites registran típicamente a $10\text{ m}$ de altura ($z_{ref}$). Las turbinas industriales tienen su buje (*hub*) a $80\text{ m} - 120\text{ m}$. El viento a la altura del buje se calcula mediante:

$$v(z) = v(z_{ref}) \cdot \frac{\ln(z / z_0)}{\ln(z_{ref} / z_0)}$$

Para Uribia, la rugosidad de superficie se modela como $z_0 = 0.03\text{ m}$ (terreno plano semidesértico con vegetación baja).

### 3.3. Curva de Potencia Aerodinámica de la Turbina
El modelo evalúa una turbina industrial clase IEC S adaptada a los vientos de La Guajira:
* **Potencia Nominal:** $3.0\text{ MW}$ ($3000\text{ kW}$).
* **Diámetro de Rotor:** $112\text{ m}$ (Área barrida $A = 9852\text{ m}^2$).
* **Coeficiente Aerodinámico ($C_p$):** $0.42$.

La generación eléctrica responde a cuatro zonas físicas:
1. **Zona I ($v < 3.5\text{ m/s}$):** *Sub-Cut-In*. La velocidad no vence la inercia del tren de potencia ($P = 0\text{ kW}$).
2. **Zona II ($3.5 \le v < 12.0\text{ m/s}$):** Régimen aerodinámico cúbico con control de velocidad variable:
   $$P(v) = \frac{1}{2} \cdot \rho \cdot A \cdot v^3 \cdot C_p$$
3. **Zona III ($12.0 \le v \le 25.0\text{ m/s}$):** Potencia nominal constante ($P = 3000\text{ kW}$) mediante control de ángulo de pala (*pitch control*).
4. **Zona IV ($v > 25.0\text{ m/s}$):** Freno mecánico y aerodinámico por seguridad ante ráfagas extremas (*Super-Cut-Out*).

### 3.4. Balance Energético y Métricas de Factibilidad
Para cada una de las 24 horas del día:
$$\Delta E(t) = P_{generada}(t) - P_{demanda}(t)$$

* **Cobertura Diaria:**
  $$\text{Cobertura (\%)} = \left(\frac{E_{producida}}{E_{demanda}}\right) \times 100$$
* **Autonomía Nominal:** Cuántas horas completas de proceso industrial sostiene la energía generada en la jornada:
  $$\text{Autonomía (horas)} = \frac{E_{producida}}{\overline{E}_{demanda / hora}}$$
* **Excedente ($\Delta E > 0$):** Energía disponible para inyección al Sistema Interconectado Nacional (SIN) o almacenamiento en baterías BESS.
* **Déficit ($\Delta E < 0$):** Requerimiento de respaldo de red o descarga del banco de baterías.

---

## 4. Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.10 o superior.

### 1. Clonar el repositorio
```bash
git clone https://github.com/jrecchiavlla1235-droid/PIPELIN-PARQUE-WINDPESHI.git
cd PIPELIN-PARQUE-WINDPESHI
```

### 2. Crear entorno virtual (Recomendado)
```bash
python -m venv venv

# En Windows:
.\venv\Scripts\activate

# En Linux/macOS:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## 5. Guía de Uso del CLI (`main.py`)

El punto de entrada principal permite parametrizar tanto el análisis del parque como el balance industrial.

### A. Balance Energético Industrial (Modo por defecto)
Ejecuta la factibilidad para la fecha de hoy en Uribia con la maquinaria por defecto:
```bash
python main.py --mode balance
```

### B. Personalizar la Potencia y Operación de la Empresa
Simular una planta con $1500\text{ kW}$ de carga activa y $18\text{ horas}$ de operación diaria:
```bash
python main.py --mode balance --power 1500 --hours 18
```

### C. Evaluar una Fecha Histórica Específica
```bash
python main.py --mode balance --date 2026-03-24 --power 1200
```

### D. Modo de Evaluación Clásica del Parque (Favorabilidad)
Evalúa las horas de generación útil vs. percentil P50 del recurso eólico:
```bash
python main.py --mode evaluation
```

---

## 6. Salidas y Entregables del Pipeline

Cada ejecución genera automáticamente:
1. **Informe en Consola:** Resumen ejecutivo con KPIs climáticos, balance neto, horas de autonomía y dimensionamiento de BESS.
2. **Dataset Tabular Procesado (`data/processed/energy_balance_YYYY-MM-DD.csv`):** Las 24 horas con todas las variables climáticas, densidad del aire, $GHI$, potencias y saldo neto.
3. **Gráfico Analítico de Alta Resolución (`reports/balance_energetico_uribia_YYYY-MM-DD.png`):** Curva comparativa de 24 horas generada con Seaborn/Matplotlib destacando áreas de excedentes (verde) y déficit (naranja).
4. **Caché Meteorológico (`data/cache/climate_uribia_YYYY-MM-DD.json`):** Asegura ejecuciones instantáneas y soporte offline.

---

## 7. Licencia y Créditos
Desarrollado para el análisis de factibilidad y toma de decisiones energéticas en proyectos de energía renovable en Colombia.
