# Passionwaves Media

A static site you write in Markdown. Run one command, upload one folder. No HTML editing, no servers, no pip installs.

## Folder map

```
site.json         ← all your settings + homepage copy (edit this)
content/          ← your articles, as .md files (write these)
assets/styles.css ← the look (edit rarely)
assets/app.js     ← behavior: filter, likes, views
build.py          ← run this to generate the site
public/           ← the generated site — THIS is what you upload to S3
```

## Publishing an article — the whole workflow

1. Create `content/my-new-post.md`:

   ```
   ---
   title: My new post
   slug: my-new-post
   category: Travel
   excerpt: One or two sentences shown on the card and as the subtitle.
   date: 2026-08-01
   featured: true      # optional — puts it in the big top slot
   ---

   Your article in **Markdown**. Headings with #, lists with -, quotes with >,
   `inline code`, [links](https://example.com), and images all work.
   ```

2. Run:

   ```
   python3 build.py
   ```

3. Upload everything in `public/` to your S3 bucket. Done.

`category` must match one of the categories in `site.json`. Reading time is calculated automatically. Articles sort newest-first.

## The homepage vs. the "All articles" page

The site now has two views, so a big archive never dumps onto the homepage:

- **Homepage** shows the featured piece plus the **6 most recent** articles, then a
  "Browse all articles" button. To change how many appear, edit the `[:6]` in
  `build.py` (in `build_index`).
- **articles.html** is the full archive — the "Read" tab in the header points here.
  Every article is listed, **grouped by category**, with filter chips at the top.
  Any category with more than **12** articles shows the first 12 and a "Show all"
  button (change the `12` in `build_index`'s `build_archive`). Footer category links
  jump straight to that category and pre-filter it.

Both pages regenerate automatically when you run `python3 build.py`. With text-only
cards, even a few hundred articles load instantly; if you ever grow into the many
hundreds, per-category pages or paginated pages are a small addition — just ask.

## Adding or renaming categories

In `site.json`, edit the `categories` block — each is a name and a color. The filter chips, dots, and footer update themselves on the next build.

```json
"categories": { "AWS": "#6B4EE6", "Travel": "#22B0C4", "Music": "#3BB273" }
```

## LinkedIn & X links

In `site.json` under `social`, replace the two placeholder URLs with your real profiles. They appear in the footer with icons. Leave one blank to hide it.

## Email signup — 5-minute setup (optional)

The signup form is already on the page; it just needs somewhere to send emails. The no-backend way:

1. Make a free account at **Buttondown** (simplest), **Kit**, or **MailerLite**.
2. Find your form's action URL. In Buttondown it looks like
   `https://buttondown.com/api/emails/embed-subscribe/YOUR-USERNAME`.
3. Paste it into `site.json` → `newsletter.action`, and rebuild.

That's it — submissions go straight to your provider, no server involved. If the
field name your provider expects isn't `email`, change the `name="email"` input in
`build.py` (one spot). To remove signup entirely, set `newsletter.enabled` to `false`.

## Likes & views — 5-minute setup (optional)

Because the site is static, shared counts need a tiny free datastore. **Supabase**
is the easiest (no server to run). Without it, the like button still works per-browser;
view counts just stay hidden.

1. Create a free project at supabase.com. Copy the Project URL and the `anon` public key
   into `site.json` → `supabase`.
2. In the Supabase SQL editor, run:

   ```sql
   create table stats (slug text primary key, likes int default 0, views int default 0);
   alter table stats enable row level security;

   create or replace function pw_view(p_slug text)
   returns table(likes int, views int) language plpgsql security definer as $$
   begin
     insert into stats(slug, views) values (p_slug, 1)
     on conflict (slug) do update set views = stats.views + 1;
     return query select s.likes, s.views from stats s where s.slug = p_slug;
   end; $$;

   create or replace function pw_like(p_slug text)
   returns table(likes int, views int) language plpgsql security definer as $$
   begin
     insert into stats(slug, likes) values (p_slug, 1)
     on conflict (slug) do update set likes = stats.likes + 1;
     return query select s.likes, s.views from stats s where s.slug = p_slug;
   end; $$;

   grant execute on function pw_view(text), pw_like(text) to anon;
   ```

3. Rebuild. Likes and reads now count for real, shared across everyone.

The `anon` key is safe to ship in a public site — it can only call those two
functions, nothing else. One like per browser is enforced client-side.

## Going live on S3

1. Set your real `domain` in `site.json` and rebuild.
2. Upload the contents of `public/` to your S3 bucket (static website hosting on,
   index document `index.html`).
3. Put CloudFront in front for HTTPS + your custom domain.
