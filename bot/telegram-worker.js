/**
 * BCONHUB Telegram Report Bot — Cloudflare Worker
 *
 * Deployment: paste this whole file into a Cloudflare Worker (dashboard -> Workers & Pages ->
 * Create -> Edit code), then set two secrets on the worker (Settings -> Variables -> Encrypt):
 *   TELEGRAM_BOT_TOKEN  - the token BotFather gave you
 *   WEBHOOK_SECRET      - any random string you make up (used to verify requests really came
 *                         from Telegram; Telegram echoes it back in a header on every call)
 *
 * After deploying, register the webhook once by visiting (replace both placeholders):
 *   https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_WORKER_URL>&secret_token=<WEBHOOK_SECRET>
 *
 * Zero ongoing cost: Cloudflare Workers' free tier (100,000 requests/day) covers this easily,
 * and reading Reports/ from GitHub uses the public, unauthenticated contents API - no GitHub
 * token needed since this is a public repo.
 */

const GITHUB_REPO = "rakeshbob007/Bristlecone-Intelligence-HUB";
const REPORTS_API_URL = `https://api.github.com/repos/${GITHUB_REPO}/contents/Reports`;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // GET /whoami - confirms the stored TELEGRAM_BOT_TOKEN is actually valid, without
    // exposing the token itself. Visit this in any ordinary browser.
    if (request.method === "GET" && url.pathname === "/whoami") {
      const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getMe`);
      const body = await resp.text();
      return new Response(body, { status: resp.status, headers: { "Content-Type": "application/json" } });
    }

    // GET /setup - registers THIS worker's URL as the bot's webhook, calling Telegram's API
    // from Cloudflare's network (not the visitor's), which sidesteps any local network block
    // on api.telegram.org. Visit this once, in any ordinary browser, after deploying.
    if (request.method === "GET" && url.pathname === "/setup") {
      const webhookUrl = `${url.origin}/`;
      const setupResp = await fetch(
        `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/setWebhook?url=${encodeURIComponent(webhookUrl)}&secret_token=${encodeURIComponent(env.WEBHOOK_SECRET)}`
      );
      const body = await setupResp.text();
      return new Response(body, { status: setupResp.status, headers: { "Content-Type": "application/json" } });
    }

    if (request.method !== "POST") {
      return new Response("BCONHUB Telegram bot is running.", { status: 200 });
    }

    // Reject anything that isn't really from Telegram.
    const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (secret !== env.WEBHOOK_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("Bad request", { status: 400 });
    }

    const message = update.message;
    if (!message || !message.text) {
      return new Response("OK", { status: 200 }); // ignore non-text updates
    }

    const chatId = message.chat.id;
    const text = message.text.trim().toLowerCase();

    try {
      if (text === "/start" || text === "/help") {
        await sendMessage(env, chatId,
          "👋 I'm the BCONHUB Reports bot.\n\nSend /latest to get the most recent BCONHUB Intelligence Report.");
      } else if (text === "/latest" || text === "/report") {
        await sendLatestReport(env, chatId);
      } else {
        await sendMessage(env, chatId, "Not sure what you mean — send /latest to get the newest report.");
      }
    } catch (err) {
      // Always ack Telegram even if something downstream failed, so it doesn't retry-storm us.
      console.error(err);
    }

    return new Response("OK", { status: 200 });
  },
};

async function sendLatestReport(env, chatId) {
  const headers = { "User-Agent": "bconhub-telegram-bot" };
  if (env.GITHUB_TOKEN) headers["Authorization"] = `Bearer ${env.GITHUB_TOKEN}`;
  const listResp = await fetch(REPORTS_API_URL, { headers });
  if (!listResp.ok) {
    await sendMessage(env, chatId, "Couldn't reach the Reports folder on GitHub right now — try again shortly.");
    return;
  }

  const files = await listResp.json();
  const reports = files
    .filter((f) => f.type === "file" && /^BCONHUB-Report_.*\.html$/.test(f.name))
    .sort((a, b) => (a.name < b.name ? 1 : -1)); // filenames are date/time-sortable, newest first

  if (reports.length === 0) {
    await sendMessage(env, chatId, "No reports found yet in the Reports folder.");
    return;
  }

  const latest = reports[0];
  const rawUrl = `https://raw.githubusercontent.com/${GITHUB_REPO}/main/Reports/${latest.name}`;

  // Telegram's servers often fail to fetch files by URL from raw.githubusercontent.com directly
  // ("Bad Request: failed to get HTTP URL content"), so download the file here and upload the
  // actual bytes instead of just passing the URL along.
  const fileResp = await fetch(rawUrl, { headers: { "User-Agent": "bconhub-telegram-bot" } });
  if (!fileResp.ok) {
    await sendMessage(env, chatId, `Couldn't download the report from GitHub (status ${fileResp.status}). Try /latest again shortly.`);
    return;
  }
  const fileBuffer = await fileResp.arrayBuffer();

  const result = await sendDocument(env, chatId, fileBuffer, latest.name, `📰 Latest BCONHUB report: ${latest.name}`);
  if (!result.ok) {
    // Surface the real Telegram error instead of failing silently.
    await sendMessage(env, chatId, `Couldn't send the file (Telegram said: ${result.description}). Try /latest again shortly.`);
  }
}

async function sendMessage(env, chatId, text) {
  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
  const data = await resp.json();
  if (!data.ok) console.error("sendMessage failed:", JSON.stringify(data));
  return data;
}

async function sendDocument(env, chatId, fileBuffer, filename, caption) {
  const form = new FormData();
  form.append("chat_id", String(chatId));
  form.append("caption", caption);
  form.append("document", new Blob([fileBuffer], { type: "text/html" }), filename);

  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendDocument`, {
    method: "POST",
    body: form,
  });
  const data = await resp.json();
  if (!data.ok) console.error("sendDocument failed:", JSON.stringify(data));
  return data;
}
