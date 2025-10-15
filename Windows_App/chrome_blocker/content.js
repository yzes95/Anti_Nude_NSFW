// content.js
(async function() {
  try {
    // quick text scan
    const text = document.body.innerText || "";
    const explicitWords = ["porn","xxx","nude","sex","nsfw","boobs","cock","pussy"];
    const lower = text.toLowerCase();
    for (let w of explicitWords) {
      if (lower.includes(w)) {
        // redirect to blank or show block overlay
        document.documentElement.innerHTML = "<h1 style='text-align:center;margin-top:20vh;'>Blocked by NSFW guard</h1>";
        return;
      }
    }

    // sample: analyze main images on page (do first N images)
    const imgs = Array.from(document.images).slice(0,6);
    for (let img of imgs) {
      try {
        // draw to canvas to get data URL
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth || 640;
        canvas.height = img.naturalHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
        // send to local detector
        const resp = await fetch("http://127.0.0.1:5000/analyze", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({image_b64: dataUrl})
        });
        const j = await resp.json();
        if (j.block) {
          document.documentElement.innerHTML = "<h1 style='text-align:center;margin-top:20vh;'>Blocked by NSFW guard (server)</h1>";
          return;
        }
      } catch(e){
        console.log("image check error", e);
      }
    }
  } catch(e) {
    console.log("content script error", e);
  }
})();
