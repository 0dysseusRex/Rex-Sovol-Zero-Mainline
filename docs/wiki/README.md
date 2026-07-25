# Wiki source files

This folder is the **source of truth** for the GitHub Wiki:

**https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/wiki**

## One-time setup (repo maintainer)

GitHub requires **one manual click** to create the wiki git repository before automation can push:

1. Open **[Create first wiki page](https://github.com/0dysseusRex/Rex-Sovol-Zero-Mainline/wiki/_new)**
2. Title: `Home`
3. Body: `Wiki initializing…` (any placeholder text)
4. Click **Save Page**

Then either:

- **Automatic:** push to `master` with changes under `docs/wiki/` — the [Publish Wiki](../../.github/workflows/publish-wiki.yml) Action syncs to the Wiki tab, or  
- **Manual:** Actions → **Publish Wiki** → **Run workflow**

## Editing the wiki

1. Edit markdown files in this directory (`docs/wiki/`).
2. Commit and push to `master`.
3. The GitHub Action republishes the Wiki tab.

Start reading at [Home.md](Home.md) (renders as wiki **Home** page).

## Page index

| File | Wiki page |
|---|---|
| `Home.md` | Home |
| `Before-You-Begin.md` | Before You Begin |
| `SSH-and-Networking-Basics.md` | SSH and Networking Basics |
| `Backup-and-Recovery.md` | Backup and Recovery |
| `ST-LINK-Step-by-Step.md` | ST-LINK Step by Step |
| `Host-Setup-CB1-Armbian.md` | Host Setup (CB1 / Armbian) |
| `Installing-the-Klipper-Stack.md` | Installing the Klipper Stack |
| `CAN-Bus-and-MCU-Flashing.md` | CAN Bus and MCU Flashing |
| `Configuration-and-Rex-Repo.md` | Configuration and Rex Repo |
| `Calibration.md` | Calibration |
| `Troubleshooting.md` | Troubleshooting |
| `Credits-and-Resources.md` | Credits and Resources |
| `_Sidebar.md` | Wiki sidebar navigation |
