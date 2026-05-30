# 🌡️ Ilhas de Calor Urbanas — Jundiaí/SP

Painel interativo para análise e visualização de ilhas de calor urbanas
no município de Jundiaí/SP, desenvolvido como produto do projeto de
pesquisa sobre SUHI (Surface Urban Heat Island).

---

## Estrutura do projeto

```
jundiai-uhi-app/
├── app.py                        # App principal Streamlit
├── utils/
│   ├── data_loader.py            # Carrega TIFs (local ou Google Drive)
│   ├── raster_utils.py           # Hotspots, persistência, anomalia
│   └── map_builder.py            # Constrói mapas Leafmap interativos
├── data/                         # TIFs ficam aqui (não vai ao GitHub)
├── .streamlit/
│   ├── config.toml               # Tema e configurações
│   └── secrets.toml.example      # Template dos IDs do Drive
├── requirements.txt
└── README.md
```

---

## Como rodar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/SEU_USUARIO/jundiai-uhi-app.git
cd jundiai-uhi-app
```

### 2. Crie um ambiente virtual e instale as dependências

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Adicione os dados

**Opção A — Arquivos locais (recomendado para desenvolvimento):**

Copie os TIFs gerados pelo Notebook Parte 1 para a pasta `data/`:

```
data/
├── Jundiai_SUHI_2017.tif
├── Jundiai_SUHI_2019.tif
├── Jundiai_SUHI_2021.tif
├── Jundiai_SUHI_2023.tif
├── Jundiai_SUHI_2025.tif
├── Jundiai_MapBiomas_2017.tif
├── Jundiai_MapBiomas_2019.tif
├── Jundiai_MapBiomas_2021.tif
├── Jundiai_MapBiomas_2023.tif
└── Jundiai_MapBiomas_2025.tif
```

**Opção B — Download automático do Google Drive:**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edite secrets.toml com os IDs dos arquivos no Drive
```

Para obter o ID de um arquivo no Drive:
1. Clique com botão direito → Compartilhar → Copiar link
2. O link tem formato `https://drive.google.com/file/d/ID_AQUI/view`
3. Cole o `ID_AQUI` no secrets.toml

Os arquivos precisam estar compartilhados como **"Qualquer pessoa com o link"**.

### 4. Rode o app

```bash
streamlit run app.py
```

Abra `http://localhost:8501` no navegador.

---

## Deploy no Streamlit Cloud (URL pública)

1. Faça push do repositório para o GitHub (sem a pasta `data/` e sem `secrets.toml`)
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte sua conta GitHub e selecione o repositório
4. Em **Advanced settings → Secrets**, cole o conteúdo do seu `secrets.toml`
5. Clique em **Deploy** — em ~2 minutos você terá uma URL pública

> Os TIFs serão baixados automaticamente do Google Drive na primeira vez que
> alguém acessar o app. O cache do Streamlit evita downloads repetidos.

---

## Páginas do painel

| Página | Descrição |
|--------|-----------|
| 🌡️ Temperatura e Hotspots | LST, NDVI, NDBI, MNDWI por ano com hotspots sobrepostos |
| 📍 Persistência de Hotspots | Acúmulo de anos como hotspot (0 a 5) — núcleos crônicos em vermelho escuro |
| 🔬 Resíduos do Modelo RF | Onde o Random Forest sub/superestima a temperatura (2025) |

---

## Dados necessários

| Arquivo | Origem | Bandas |
|---------|--------|--------|
| `Jundiai_SUHI_AAAA.tif` | Notebook Parte 1 (GEE) | 1=LST, 2=NDVI, 3=NDBI, 4=MNDWI |
| `Jundiai_MapBiomas_AAAA.tif` | Bloco E (GEE) | 1=Classe MapBiomas |

---

## Dependências principais

- **Streamlit** — framework web
- **Leafmap** — wrapper sobre Folium/Leaflet para mapas interativos
- **Rasterio** — leitura e processamento de GeoTIFFs
- **gdown** — download de arquivos do Google Drive
