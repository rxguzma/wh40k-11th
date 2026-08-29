# WH40k 11th companion

Personal table app. Army data still comes from the Google Sheets already wired in the HTML.

## Play URL

https://rxguzma.github.io/wh40k-11th/

Bookmark that on the phone. Rosters stay in the browser (IndexedDB).

## Loop

1. Chat with Grok in this project.
2. Grok commits the HTML here as `index.html` and bumps `version.json`.
3. GitHub Pages publishes it.
4. In the app, open **Roster** and tap **Update app**.

First time only: GitHub → repo **Settings** → **Pages** → Source **GitHub Actions**. Then run the **Deploy Pages** workflow if the play URL 404s.

## Files

| File | Role |
| --- | --- |
| `index.html` | The companion app |
| `version.json` | What the Update button checks |
| Spreadsheets | Stay in Google Sheets / this Grok project, not this repo |
