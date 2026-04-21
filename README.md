# Quattro Tax — Sistema de Preparación 2025

App web para preparar declaraciones de impuestos. Lee documentos con IA y genera PDFs del IRS pre-llenados.

## Deploy en Railway (gratis)

1. Sube este proyecto a GitHub
2. Ve a railway.app → New Project → Deploy from GitHub
3. Selecciona este repo
4. Railway detecta automáticamente que es Python y lo instala
5. En Settings → Variables, agrega: `ANTHROPIC_API_KEY` (opcional, el usuario la provee en la app)
6. Tu URL aparece en Settings → Domains

## Uso local

```bash
pip install -r requirements.txt
python app.py
```
Abre http://localhost:5000

## Estructura

```
app.py                 — Backend Flask
requirements.txt       — Dependencias Python
Procfile               — Config para Railway/Heroku
quattro_autofill.py    — Motor de llenado de PDFs
fill_fillable_fields.py — Script helper para PDFs
templates/index.html   — App web (frontend)
f1040.pdf, f1040sc.pdf, etc. — Forms del IRS 2025
```
