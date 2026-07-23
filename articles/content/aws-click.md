---
title: The AWS idea that finally made the cloud click for me
slug: aws-click
category: AWS
excerpt: Forget the jargon. Here's the one mental model that turned a wall of services into something I could actually reason about.
date: 2026-07-01
featured: true
---

The first time I opened the AWS console, I closed it again within a minute. There were what felt like two hundred services, each with a three-letter name, and no obvious place to start. I didn't need a tutorial. I needed a way to think about the whole thing that didn't make me want to lie down.

Here's the shift that did it: stop treating AWS as a catalog of products, and start treating it as a set of answers to very ordinary questions. *Where do my files live? Where does my code run? Who's allowed to touch what?* Almost every service is just a specific answer to one of those.

## Files, compute, permissions

Once I sorted the services into those three buckets, the fog lifted. Storage is where things sit still. Compute is where things happen. And permissions are the rules about who gets to do either.

> You don't have to understand all of AWS. You have to understand the question each piece is answering.

That's the whole trick, and it's the reason I can now read a new service's docs and place it in about thirty seconds. Not because I'm clever — because I finally had somewhere to put it.

If you're staring at that console feeling the same way I did, start with one file in one bucket. Get it online. The rest is just more of the same idea, spreading outward.
