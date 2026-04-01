let currentInterval = null;

// 🎬 Fetch video info
function fetchInfo() {
    const url = document.getElementById("url").value;

    if (!url) {
        alert("Enter URL");
        return;
    }

    // reset UI
    document.getElementById("quality").innerHTML = "";
    document.getElementById("title").innerText = "";
    document.getElementById("thumbnail").src = "";

    fetch('/get_info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    })
    .then(res => res.json())
    .then(data => {

        console.log("FETCH:", data);

        if (data.error) {
            alert(data.error);
            return;
        }

        document.getElementById("title").innerText = data.title;
        document.getElementById("thumbnail").src = data.thumbnail;

        // create hidden input if not exists
        let hidden = document.getElementById("hiddenUrl");
        if (!hidden) {
            hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.id = "hiddenUrl";
            document.body.appendChild(hidden);
        }
        hidden.value = url;

        const select = document.getElementById("quality");
        select.innerHTML = "";

        if (!data.qualities || data.qualities.length === 0) {
            const option = document.createElement("option");
            option.text = "No quality available";
            select.appendChild(option);
            return;
        }

        data.qualities.forEach(q => {
            const option = document.createElement("option");
            option.value = q.quality;
            option.text = `${q.quality} (${q.size})`;
            select.appendChild(option);
        });

    })
    .catch(err => {
        console.error(err);
        alert("Fetch failed");
    });
}

// ⬇ Start download
function startDownload() {
    const url = document.getElementById("hiddenUrl").value;
    const quality = document.getElementById("quality").value;
    const btn = document.getElementById("downloadBtn");

    if (!url) {
        alert("Fetch video first!");
        return;
    }

    // 🔥 Spinner ON
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Downloading...';

    // reset progress UI
    document.getElementById("progressBar").style.width = "0%";
    document.getElementById("progressText").innerText = "0 MB / 0 MB";
    document.getElementById("speedText").innerText = "Speed: 0 MB/s";
    document.getElementById("etaText").innerText = "ETA: 0 sec";

    fetch('/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `url=${url}&quality=${quality}`
    })
    .then(res => res.json())
    .then(data => {

        console.log("DOWNLOAD:", data);

        if (data.error) {
            alert(data.error);

            // 🔥 Reset button on error
            btn.disabled = false;
            btn.innerHTML = "⬇ Download";
            return;
        }

        trackProgress(data.id);
    });
}

// 📊 Track progress
function trackProgress(id) {

    if (currentInterval) {
        clearInterval(currentInterval);
    }

    currentInterval = setInterval(() => {

        fetch(`/progress/${id}`)
        .then(res => res.json())
        .then(data => {

            if (!data.total) return;

            const downloaded = (data.downloaded / (1024 * 1024)).toFixed(2);
            const total = (data.total / (1024 * 1024)).toFixed(2);

            document.getElementById("progressText").innerText =
                `${downloaded} MB / ${total} MB`;

            document.getElementById("speedText").innerText =
                `Speed: ${data.speed} MB/s`;

            document.getElementById("etaText").innerText =
                `ETA: ${data.eta} sec`;

            const percent = (data.downloaded / data.total) * 100;
            document.getElementById("progressBar").style.width = percent + "%";

            // 🔥 When done
            if (data.done) {
                clearInterval(currentInterval);

                const btn = document.getElementById("downloadBtn");
                btn.disabled = false;
                btn.innerHTML = "⬇ Download";

                // small delay for smooth UX
                setTimeout(() => {
                    window.location.href = `/get_file/${id}`;
                }, 300);
            }

        });

    }, 1000);
}
