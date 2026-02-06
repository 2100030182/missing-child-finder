function loadMissingChildren() {
  fetch("/missing-children")
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById("missingList");
      container.innerHTML = "";

      if (data.length === 0) {
        container.innerHTML = "<p>No missing children reported.</p>";
        return;
      }

      data.forEach(child => {
        const card = document.createElement("div");
        card.className = "missing-card";

        card.innerHTML = `
          <img src="${child.image}">
          <p><strong>Guardian:</strong> ${child.name}</p>
          <p><strong>Phone:</strong> ${child.phone}</p>
          <p><strong>Email:</strong> ${child.email}</p>
        `;

        container.appendChild(card);
      });
    });
}

function clearAllData() {
  if (confirm("Are you sure you want to clear ALL data?")) {
    fetch("/reset-all", { method: "POST" })
      .then(() => location.reload());
  }
}

function compareFaces() {
  const fileInput = document.getElementById("missingImage");
  const result = document.getElementById("result");
  const clearMatchBtn = document.getElementById("clearMatchBtn");

  clearMatchBtn.style.display = "none";

  if (!fileInput.files[0]) {
    result.innerText = "⚠️ Please upload an image first.";
    return;
  }

  // 🔵 SHOW LOADING MESSAGE
  result.innerText = "⏳ Please wait... finding possible matches.";

  const formData = new FormData();
  formData.append("image", fileInput.files[0]);

  fetch("/compare", {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {

      // 🟢 MATCH FOUND
      if (data.match === true) {
        let output = "✅ MATCH FOUND\n\n";
        data.results.forEach((r, i) => {
          output += `Match ${i + 1}\n`;
          output += `Finder: ${r.finder_name}\n`;
          output += `Phone: ${r.phone}\n`;
          output += `Email: ${r.email}\n`;
          output += `Found at: ${r.found_location}\n`;
          output += `Collect at: ${r.collect_location}\n\n`;
        });

        result.innerText = output;

        // ENABLE OPTION 2 ONLY AFTER MATCH
        clearMatchBtn.style.display = "inline-block";
        return;
      }

      // 🔴 NO MATCH
      if (data.already_reported) {
        result.innerText =
          "❌ No match found.\nThis child is already reported missing.";
      } else {
        const confirmReport = confirm(
          "No match found.\nDo you want to report this child as missing?"
        );

        if (confirmReport) {
          window.location.href = "/upload_missing.html";
        } else {
          result.innerText = "❌ No match found.";
        }
      }
    })
    .catch(() => {
      result.innerText =
        "❌ Error occurred while finding possible matches.";
    });
}

function clearMatchedData() {
  if (confirm("Clear matched missing & found child data?")) {
    fetch("/clear-matched", { method: "POST" })
      .then(() => location.reload());
  }
}

window.onload = loadMissingChildren;
