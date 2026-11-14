# Institutional access

Elsevier decides entitlement per request, from either the **IP address** the request comes from or an **insttoken** sent with your API key.

## Option 1: campus network

On campus Wi-Fi (or wired), requests come from the university's IP range and subscribed content works. Run `doctor` there: the tier should read `fulltext`.

## Option 2: insttoken (works anywhere)

An insttoken is issued by Elsevier to your institution and linked to **your** API key. Ask your library; at UTM write to **libsupport@utm.my**. Libraries are often careful with these, so explain what you need and how the tool protects their account.

Add it with `setup`, the Claude Code plugin settings, or the config file (`ELSEVIER_INSTTOKEN=...`). Never post it publicly or share it; treat it like a password.

### Email template

Fill in the `{...}` parts and send it from your institutional email address. Do **not** include your API key.

```text
Subject: Request for an Elsevier API insttoken for text mining / research

Dear Library team,

I am a {postgraduate student / staff member} at {faculty / department}, {student or staff ID},
working on {thesis or project title}, supervised by {supervisor}.

I use the official Elsevier APIs (Scopus Search, Abstract Retrieval and ScienceDirect Article
Retrieval) for my literature review, through an open-source tool
(https://github.com/danialkamarolzaman/elsevier-research-mcp-utm). I already have a personal API
key registered at dev.elsevier.com under my institutional email.

Off-campus, the key only gives metadata. Could the library request an institutional token
(insttoken) from Elsevier linked to my API key, so that I can retrieve full text of subscribed
journals from home?

The tool enforces the library's e-resource rules on my side: at most 5 articles and 100 MB in any
15 minutes, at most 20 articles per day, one request at a time with a 10-second gap, no scraping
or bulk downloading, and no sharing of downloaded content. I expect to need roughly {N} articles
over {period}.

I am happy to provide anything else you need.

Thank you,
{name}
{contact details}
```

## About VPNs

A university VPN only helps if it routes **all** traffic through the campus network (full tunnel). Many are **split tunnel**: only campus systems go through the VPN, and Elsevier still sees your home IP. You can check: with the VPN on, look up your public IP (for example at a "what is my IP" site). If it shows your home provider, the VPN will not unlock full text, and `doctor` will still report `metadata`.

## EZproxy links

Every paper includes `proxy_url`, an EZproxy starting-point link (UTM: `ezproxy.utm.my`). Open it in your browser and log in with your library account as usual. The tool itself never logs in to EZproxy or downloads through it, because that would break library rules on automated access. Set `ERM_PROXY_HOST` to your own library's proxy host, or to empty to turn the links off.

## Other institutions

The download limits default to the UTM Library rules. Set `ERM_MAX_ARTICLES_PER_WINDOW`, `ERM_MAX_MB_PER_WINDOW`, `ERM_WINDOW_MINUTES`, `ERM_MAX_ARTICLES_PER_DAY` and `ERM_MIN_DELAY_SECONDS` to your library's rules. Only raise them if your library allows it.
