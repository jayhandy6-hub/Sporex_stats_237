document.getElementById("btn").addEventListener("click", async () => {
  const result = document.getElementById("result");
  result.innerHTML = "⏳ Chargement...";
  const res = await fetch("/api/analyze");
  const data = await res.json();

  if (data.error) {
    result.innerHTML = `<p>${data.error}</p>`;
  } else {
    result.innerHTML = `
      <h2>${data.topic}</h2>
      <h3>${data.title}</h3>
      <p>${data.analysis}</p>
      <a href="${data.url}" target="_blank">Lire l’article complet</a>
      <p><em>Source : ${data.source}</em></p>
    `;
  }
});
