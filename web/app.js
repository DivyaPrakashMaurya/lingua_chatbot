const $ = (id) => document.getElementById(id);
const state = { id: null, conversation: null, busy: false, health: null };
async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "The request could not be completed. Please try again.",
    );
  }
  return response.status === 204 ? null : response.json();
}
function fail(error) {
  $("error").textContent = error.message;
  $("error").hidden = false;
}
function clearError() {
  $("error").hidden = true;
}
function busy(value) {
  state.busy = value;
  $("send").disabled = value;
  $("new-chat").disabled = value;
  $("message").disabled = value;
  document
    .querySelectorAll("[data-prompt],.history-open,.history-delete")
    .forEach((b) => (b.disabled = value));
}
function reset() {
  if (state.busy) return;
  state.id = null;
  state.conversation = null;
  localStorage.removeItem("lingua-conversation");
  render();
  $("message").focus();
  $("sidebar").classList.remove("open");
}
async function refresh() {
  const conversations = await api("/conversations");
  $("history").replaceChildren();
  if (!conversations.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Your conversations will appear here.";
    $("history").append(p);
  }
  for (const c of conversations) {
    const row = document.createElement("div");
    row.className = "history-row" + (state.id === c.id ? " active" : "");
    const open = document.createElement("button");
    open.className = "history-open";
    open.textContent = c.title;
    open.title = c.title;
    open.disabled = state.busy;
    open.onclick = () => load(c.id);
    const del = document.createElement("button");
    del.className = "history-delete";
    del.textContent = "×";
    del.setAttribute("aria-label", "Delete " + c.title);
    del.disabled = state.busy;
    del.onclick = async () => {
      if (
        state.busy ||
        !confirm("Delete this conversation? This cannot be undone.")
      )
        return;
      try {
        await api("/conversations/" + c.id, { method: "DELETE" });
        if (state.id === c.id) reset();
        await refresh();
      } catch (e) {
        fail(e);
      }
    };
    row.append(open, del);
    $("history").append(row);
  }
}
async function load(id) {
  if (state.busy) return;
  clearError();
  busy(true);
  try {
    const c = await api("/conversations/" + id);
    state.id = id;
    state.conversation = c;
    localStorage.setItem("lingua-conversation", id);
    render();
    await refresh();
    $("sidebar").classList.remove("open");
  } catch (e) {
    fail(e);
  } finally {
    busy(false);
  }
}
function render() {
  const messages = state.conversation?.messages || [];
  $("welcome").hidden = messages.length > 0;
  $("messages").replaceChildren();
  $("chat-title").textContent = state.conversation?.title || "New conversation";
  for (const m of messages) {
    const row = document.createElement("article");
    row.className = "message " + m.role;
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = m.role === "user" ? "Y" : "✳";
    const body = document.createElement("div");
    body.className = "message-body";
    const name = document.createElement("div");
    name.className = "message-name";
    name.textContent = m.role === "user" ? "You" : "Lingua";
    if (m.role === "assistant") {
      const mode = document.createElement("small");
      mode.textContent =
        m.metadata.mode === "demo" ? "Demo response" : "AI response";
      name.append(mode);
    }
    const content = document.createElement("div");
    content.className = "message-content";
    content.dir = "auto";
    content.textContent = m.content;
    body.append(name, content);
    if (m.role === "assistant") {
      const copy = document.createElement("button");
      copy.className = "copy-message";
      copy.textContent = "Copy response";
      copy.onclick = async () => {
        try {
          await navigator.clipboard.writeText(m.content);
          copy.textContent = "Copied";
          setTimeout(() => (copy.textContent = "Copy response"), 1800);
        } catch (e) {
          fail(
            new Error(
              "Copy is unavailable in this browser. Select the response text to copy it.",
            ),
          );
        }
      };
      body.append(copy);
    }
    row.append(avatar, body);
    $("messages").append(row);
  }
  const meta = [...messages]
    .reverse()
    .find((m) => m.role === "assistant")?.metadata;
  insights(meta);
  $("export").disabled = !messages.length;
  requestAnimationFrame(
    () =>
      ($("chat-scroll").scrollTop = messages.length
        ? $("chat-scroll").scrollHeight
        : 0),
  );
}
function insights(meta) {
  const language = meta?.language;
  const languages = state.health?.languages || {};
  $("detected-language").textContent = language
    ? languages[language] ||
      (language === "und" ? "Not enough text to detect" : language)
    : "Listening for your words";
  $("language-detail").textContent = meta
    ? "Detected from your latest message. Short text may be uncertain."
    : "Write naturally. Choose a reply language below.";
  $("intent-label").textContent =
    meta?.intent?.label || "Waiting for a message";
  const confidence = meta?.intent?.confidence;
  $("intent-detail").textContent = meta
    ? confidence == null
      ? "Demo rules · no model confidence score"
      : `${Math.round(confidence * 100)}% model score · ${meta.intent.engine}`
    : "Your intent helps shape the response.";
  $("confidence-bar").style.width =
    confidence == null ? "0%" : `${confidence * 100}%`;
  const count = meta?.context_messages || 0;
  $("context-count").textContent = count;
  const window = state.health?.context_window || 12;
  $("memory-bars").replaceChildren();
  for (let i = 0; i < window; i++) {
    const bar = document.createElement("span");
    if (i < count) bar.className = "filled";
    $("memory-bars").append(bar);
  }
  $("context-detail").textContent = meta
    ? `${count} earlier messages used for this reply. Up to ${window} are retained in the model context.`
    : "A fresh start. Your next message begins the story.";
}
async function send(event) {
  event?.preventDefault();
  const message = $("message").value.trim();
  if (!message || state.busy) return;
  clearError();
  busy(true);
  let pending;
  try {
    if (!state.id) {
      const c = await api("/conversations", { method: "POST" });
      state.id = c.id;
      state.conversation = { ...c, messages: [] };
      localStorage.setItem("lingua-conversation", c.id);
    }
    $("welcome").hidden = true;
    pending = document.createElement("div");
    pending.className = "pending";
    pending.textContent =
      "Lingua is thinking… The first model response may take longer.";
    $("messages").append(pending);
    $("chat-scroll").scrollTop = $("chat-scroll").scrollHeight;
    state.conversation = await api("/conversations/" + state.id + "/messages", {
      method: "POST",
      body: JSON.stringify({ message, language: $("language").value }),
    });
    $("message").value = "";
    $("char-count").textContent = "0 / 4000";
    render();
    await refresh();
  } catch (e) {
    pending?.remove();
    $("welcome").hidden = !!state.conversation?.messages?.length;
    fail(e);
  } finally {
    busy(false);
    $("message").focus();
  }
}
$("chat-form").addEventListener("submit", send);
$("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    send();
  }
});
$("message").addEventListener("input", () => {
  $("char-count").textContent = `${$("message").value.length} / 4000`;
});
document.querySelectorAll("[data-prompt]").forEach(
  (button) =>
    (button.onclick = () => {
      $("message").value = button.dataset.prompt;
      $("message").dispatchEvent(new Event("input"));
      $("message").focus();
    }),
);
$("new-chat").onclick = () => {
  reset();
  refresh().catch(fail);
};
$("workspace-link").onclick = () => $("sidebar").classList.remove("open");
$("refresh").onclick = () => refresh().catch(fail);
$("menu-toggle").onclick = () => $("sidebar").classList.toggle("open");
$("insights-toggle").onclick = () =>
  document.body.classList.toggle(
    innerWidth <= 1000 ? "show-insights" : "insights-hidden",
  );
$("about-button").onclick = () => $("about").showModal();
$("close-about").onclick = () => $("about").close();
$("about").addEventListener("click", (e) => {
  if (e.target === $("about")) {
    const r = $("about").getBoundingClientRect();
    if (
      e.clientX < r.left ||
      e.clientX > r.right ||
      e.clientY < r.top ||
      e.clientY > r.bottom
    )
      $("about").close();
  }
});
$("export").onclick = () => {
  if (!state.conversation) return;
  const text = state.conversation.messages
    .map((m) => `${m.role === "user" ? "You" : "Lingua"}\n${m.content}`)
    .join("\n\n———\n\n");
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/plain;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "lingua-conversation.txt";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
document.addEventListener("keydown", (e) => {
  if (
    e.key.toLowerCase() === "n" &&
    !e.ctrlKey &&
    !e.metaKey &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) &&
    !$("about").open
  ) {
    reset();
    refresh().catch(fail);
  }
});
async function init() {
  try {
    state.health = await api("/health");
    const h = state.health;
    $("mode-badge").textContent =
      h.chat_mode === "demo"
        ? "Demo workspace"
        : h.chat_mode === "local"
          ? "Local AI"
          : "Hugging Face";
    $("engine-title").textContent =
      h.chat_mode === "demo"
        ? "You’re in demo mode"
        : "Your assistant is configured";
    $("engine-detail").textContent =
      h.chat_mode === "demo"
        ? "Explore the workspace. Connect a model to unlock generated responses."
        : `${h.chat_mode === "local" ? "Local Transformers" : "Hugging Face"} responses · ${h.intent_mode === "transformer" ? "transformer" : "demo"} intent handling.`;
    $("settings-info").textContent =
      `Response engine: ${h.chat_mode}. Intent engine: ${h.intent_mode}. Context window: ${h.context_window} messages.`;
    for (const [value, label] of Object.entries(h.languages)) {
      if (value === "auto") continue;
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      $("language").append(option);
    }
    await refresh();
    const saved = localStorage.getItem("lingua-conversation");
    if (saved) {
      const items = await api("/conversations");
      if (items.some((c) => c.id === saved)) await load(saved);
      else localStorage.removeItem("lingua-conversation");
    }
    render();
  } catch (e) {
    $("mode-badge").textContent = "Offline";
    $("engine-title").textContent = "Connection unavailable";
    $("engine-detail").textContent =
      "Start the FastAPI server and refresh this page.";
    fail(e);
  }
}
init();
