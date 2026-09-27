const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("q");

function addMsg(text, who, source) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  if (who === "bot") {
    const av = document.createElement("div");
    av.className = "avatar";
    av.textContent = "MF";
    div.appendChild(av);
  }
  const b = document.createElement("div");
  b.className = "bubble";
  b.append(document.createTextNode(text));
  if (source) {
    const a = document.createElement("a");
    a.className = "src";
    a.href = source;
    a.target = "_blank";
    a.rel = "noopener";
    try {
      a.textContent = "Source: " + new URL(source).pathname.replace("/mutual-funds/", "");
    } catch (e) {
      a.textContent = "Source";
    }
    b.appendChild(a);
  }
  div.appendChild(b);
  chat.appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "end" });
  return div;
}

async function ask(q) {
  q = (q || "").trim();
  if (!q) return;
  input.value = "";
  addMsg(q, "user");
  const t = addMsg("", "bot");
  t.querySelector(".bubble").innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
  try {
    const r = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q }),
    });
    const d = await r.json();
    t.remove();
    addMsg(d.answer, "bot", d.source);
  } catch (e) {
    t.remove();
    addMsg("Something went wrong reaching the assistant. Please try again.", "bot", null);
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  ask(input.value);
});
document.querySelectorAll(".examples button").forEach((b) =>
  b.addEventListener("click", () => ask(b.textContent))
);
document.querySelectorAll(".pills button").forEach((b) =>
  b.addEventListener("click", () => {
    input.value = "Tell me the expense ratio and exit load of HDFC " + b.dataset.q + ".";
    input.focus();
  })
);
