# Personal portfolio — static site

One self-contained file: `index.html`. No build step, no dependencies, no framework.
Edit it in any text editor, re-upload, done.

## Editing
Everything editable is marked with `EDIT:` comments in the source.
- **Name** — appears in `<title>`, the top-bar brand, and the footer.
- **Links** — LinkedIn, email, and GitHub. Currently placeholders (`your-handle`, `you@example.com`).
- **Sections** — Focus, Work, Writing, Certifications, Education, Beyond the cloud, Toolkit.
  Duplicate a card / row / tag block to add an item.
- **Colors & fonts** — the `:root` token block at the top. Change the accent once, it flows everywhere.
- **Left rail** — section labels live in the `SECTIONS` list in the script; keep it in sync if you rename or add a section.
- **Hero motif** — tune `CALM` (drift speed), `FADE` (opacity), and `gap` (spacing) in script block 5.
- **Writing section** — links out to PassionWaves Media, a separate site/repo (`github.com/psdilip/passionwavesmedia`)
  with its own S3 bucket and deploy workflow. The `https://passionwaves.media` links here are a placeholder until
  that site has a real domain.

Keep client names out of the Work section unless you have approval.

## Deploy to AWS S3
1. Create an S3 bucket. Under **Properties → Static website hosting**, enable it and set the index document to `index.html`.
2. Upload `index.html` (plus your résumé PDF and a favicon when ready).
3. Make it reachable — either a public-read bucket policy, or (recommended) put **CloudFront** in front for HTTPS and a custom domain via Route 53.
4. To update: edit `index.html`, re-upload. That's the whole deploy.

## Optional: remember the visitor's theme
The theme toggle follows the visitor's OS setting per session. To persist their choice
on the live site, uncomment the three `localStorage` lines in script block 4.
(Left off here because that API is blocked inside the Claude preview.)
