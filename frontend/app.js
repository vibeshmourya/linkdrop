/**
 * Universal Media Downloader - Frontend Client Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const form = document.getElementById("analyze-form");
  const urlInput = document.getElementById("url-input");
  const pasteBtn = document.getElementById("paste-btn");
  const clearBtn = document.getElementById("clear-btn");
  const analyzeBtn = document.getElementById("analyze-btn");
  const analyzeBtnText = analyzeBtn.querySelector(".btn-text");
  const analyzeBtnSpinner = analyzeBtn.querySelector(".btn-spinner");

  const statusCard = document.getElementById("status-card");
  const statusMessage = document.getElementById("status-message");
  const loadingState = document.getElementById("loading-state");
  const resultCard = document.getElementById("result-card");

  // Result Elements
  const platformBadge = document.getElementById("platform-badge");
  const mediaTypeBadge = document.getElementById("media-type-badge");
  const mediaThumbnail = document.getElementById("media-thumbnail");
  const mediaDuration = document.getElementById("media-duration");
  const mediaTitle = document.getElementById("media-title");

  // Tabs & Options
  const tabVideo = document.getElementById("tab-video");
  const tabAudio = document.getElementById("tab-audio");
  const tabImage = document.getElementById("tab-image");
  const paneVideo = document.getElementById("tab-content-video");
  const paneAudio = document.getElementById("tab-content-audio");
  const paneImage = document.getElementById("tab-content-image");
  const galleryContainer = document.getElementById("gallery-container");
  const galleryCount = document.getElementById("gallery-count");
  const galleryItemsGrid = document.getElementById("gallery-items-grid");

  const videoQualitiesList = document.getElementById("video-qualities-list");
  const audioFormatsList = document.getElementById("audio-formats-list");
  const imageFormatsList = document.getElementById("image-formats-list");

  // Download & Progress Elements
  const downloadBtn = document.getElementById("download-btn");
  const downloadBtnText = document.getElementById("download-btn-text");
  const downloadBtnSpinner = document.getElementById("download-btn-spinner");
  const progressContainer = document.getElementById("progress-container");
  const progressStage = document.getElementById("progress-stage");
  const progressPercent = document.getElementById("progress-percent");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const progressSpeed = document.getElementById("progress-speed");
  const progressSize = document.getElementById("progress-size");

  const completedContainer = document.getElementById("completed-container");
  const saveFileLink = document.getElementById("save-file-link");

  // State
  let currentAnalysisData = null;
  let activeTab = "video";
  let selectedQualityOrFormat = null;
  let progressInterval = null;

  // Input Clear / Paste behaviors
  urlInput.addEventListener("input", () => {
    if (urlInput.value.trim().length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    resultCard.classList.add("hidden");
    hideStatus();
    urlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        clearBtn.classList.remove("hidden");
        // Automatically trigger analyze
        form.dispatchEvent(new Event("submit"));
      }
    } catch (err) {
      showStatus("Could not read clipboard. Please paste manually using Ctrl+V.", "info");
    }
  });

  // Helper: Status Box
  function showStatus(message, type = "error") {
    statusMessage.textContent = message;
    statusCard.className = `status-box ${type}`;
    statusCard.classList.remove("hidden");
  }

  function hideStatus() {
    statusCard.classList.add("hidden");
  }

  // Format File Size
  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb > 1024) return (mb / 1024).toFixed(1) + " GB";
    return mb.toFixed(1) + " MB";
  }

  // Handle Form Submit -> Analyze
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rawUrl = urlInput.value.trim();
    if (!rawUrl) return;

    hideStatus();
    resultCard.classList.add("hidden");
    progressContainer.classList.add("hidden");
    completedContainer.classList.add("hidden");

    // UI Loading state
    analyzeBtn.disabled = true;
    analyzeBtnText.textContent = "ANALYZING...";
    analyzeBtnSpinner.classList.remove("hidden");
    loadingState.classList.remove("hidden");

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: rawUrl })
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || "Unable to analyze media at this URL.");
      }

      currentAnalysisData = result.data;
      renderAnalysisResult(currentAnalysisData);

    } catch (err) {
      showStatus(err.message, "error");
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtnText.textContent = "ANALYZE";
      analyzeBtnSpinner.classList.add("hidden");
      loadingState.classList.add("hidden");
    }
  });

  // Render Analysis Result
  function renderAnalysisResult(data) {
    const mediaType = (data.media_type || "").toLowerCase();

    platformBadge.textContent = data.badge || data.source || "Media";
    mediaTypeBadge.textContent = mediaType.toUpperCase();
    mediaTitle.textContent = data.title || "Public Media Resource";

    if (data.thumbnail) {
      mediaThumbnail.src = data.thumbnail;
      mediaThumbnail.classList.remove("hidden");
    } else {
      mediaThumbnail.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='60' viewBox='0 0 100 60'%3E%3Crect width='100' height='60' fill='%231e293b'/%3E%3Ctext x='50' y='35' fill='%2364748b' font-size='12' text-anchor='middle'%3EMedia%3C/text%3E%3C/svg%3E";
    }

    if (data.duration) {
      mediaDuration.textContent = data.duration;
      mediaDuration.classList.remove("hidden");
    } else {
      mediaDuration.classList.add("hidden");
    }

    // Reset all option containers
    videoQualitiesList.innerHTML = "";
    audioFormatsList.innerHTML = "";
    imageFormatsList.innerHTML = "";
    galleryItemsGrid.innerHTML = "";

    // Reset visibility of all panes and tabs
    document.getElementById("format-tabs").classList.add("hidden");
    tabVideo.classList.add("hidden");
    tabAudio.classList.add("hidden");
    tabImage.classList.add("hidden");

    paneVideo.classList.add("hidden");
    paneAudio.classList.add("hidden");
    paneImage.classList.add("hidden");
    galleryContainer.classList.add("hidden");

    // 1. GALLERY (Multiple Images or Media Items)
    if (mediaType === "gallery" || data.is_gallery) {
      activeTab = "gallery";
      selectedQualityOrFormat = "zip_all";
      galleryContainer.classList.remove("hidden");
      galleryCount.textContent = `${data.item_count || data.items.length} media items found`;

      (data.items || []).forEach((item, idx) => {
        const card = document.createElement("div");
        card.className = "gallery-item-card";

        const thumbUrl = item.thumbnail || item.url;
        if (thumbUrl) {
          const img = document.createElement("img");
          img.src = thumbUrl;
          img.className = "gallery-item-thumb";
          img.alt = item.title || `Item ${idx + 1}`;
          card.appendChild(img);
        }

        if (item.url) {
          const link = document.createElement("a");
          link.href = item.url;
          link.className = "secondary-btn gallery-item-btn";
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = `Item ${idx + 1} ↗`;
          link.title = "View item";
          card.appendChild(link);
        }

        galleryItemsGrid.appendChild(card);
      });

      downloadBtnText.textContent = `DOWNLOAD ALL (${data.item_count || data.items.length} ITEMS .ZIP)`;

    // 2. IMAGE (Single Image Post)
    } else if (mediaType === "image") {
      activeTab = "image";
      paneImage.classList.remove("hidden");

      const images = data.image_options && data.image_options.length > 0 ? data.image_options : [
        { id: "image_jpg", label: "Image (JPG)", format: "jpg" },
        { id: "image_png", label: "Image (PNG)", format: "png" },
        { id: "image_webp", label: "Image (WEBP)", format: "webp" }
      ];

      images.forEach((im, idx) => {
        const pill = createOptionPill({
          id: im.id,
          title: im.label || im.format.toUpperCase(),
          subtitle: im.format.toUpperCase(),
          name: "format_selection",
          checked: idx === 0
        });
        imageFormatsList.appendChild(pill);
      });

      selectedQualityOrFormat = images[0].id;
      downloadBtnText.textContent = "DOWNLOAD IMAGE";

    // 3. VIDEO (YouTube, Reels, Facebook, TikTok)
    } else if (mediaType === "video") {
      activeTab = "video";
      const videos = data.video_options || [];
      const audios = data.audio_options || [];

      // If video also offers audio extraction, expose clean tabs
      if (audios.length > 0) {
        document.getElementById("format-tabs").classList.remove("hidden");
        tabVideo.classList.remove("hidden");
        tabAudio.classList.remove("hidden");
        tabVideo.classList.add("active");
        tabAudio.classList.remove("active");
      }

      paneVideo.classList.remove("hidden");

      if (videos.length > 0) {
        videos.forEach((v, idx) => {
          const pill = createOptionPill({
            id: v.id,
            title: v.label,
            subtitle: v.size ? `${v.size} • ${v.format.toUpperCase()}` : v.format.toUpperCase(),
            name: "format_selection",
            checked: idx === 0
          });
          videoQualitiesList.appendChild(pill);
        });
        selectedQualityOrFormat = videos[0].id;
      }

      if (audios.length > 0) {
        audios.forEach((a, idx) => {
          const pill = createOptionPill({
            id: a.id,
            title: a.label,
            subtitle: a.format.toUpperCase(),
            name: "format_selection",
            checked: false
          });
          audioFormatsList.appendChild(pill);
        });
      }

      downloadBtnText.textContent = "DOWNLOAD VIDEO";

    // 4. AUDIO ONLY (Direct Audio files, Audio streams)
    } else if (mediaType === "audio") {
      activeTab = "audio";
      paneAudio.classList.remove("hidden");

      const audios = data.audio_options || [
        { id: "audio_mp3", label: "MP3 Audio (High Quality)", format: "mp3" },
        { id: "audio_m4a", label: "M4A Audio", format: "m4a" }
      ];

      audios.forEach((a, idx) => {
        const pill = createOptionPill({
          id: a.id,
          title: a.label,
          subtitle: a.format.toUpperCase(),
          name: "format_selection",
          checked: idx === 0
        });
        audioFormatsList.appendChild(pill);
      });

      selectedQualityOrFormat = audios[0].id;
      downloadBtnText.textContent = "DOWNLOAD AUDIO";

    // 5. UNKNOWN / UNSUPPORTED
    } else {
      throw new Error("No downloadable public media was found for this link.");
    }

    resultCard.classList.remove("hidden");
    resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Create Pill Option Helper
  function createOptionPill({ id, title, subtitle, name, checked }) {
    const label = document.createElement("label");
    label.className = `option-pill ${checked ? "selected" : ""}`;
    label.dataset.id = id;

    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = name;
    radio.value = id;
    radio.checked = checked;

    const titleEl = document.createElement("span");
    titleEl.className = "pill-title";
    titleEl.textContent = title;

    const subEl = document.createElement("span");
    subEl.className = "pill-sub";
    subEl.textContent = subtitle;

    label.appendChild(radio);
    label.appendChild(titleEl);
    label.appendChild(subEl);

    label.addEventListener("click", () => {
      const parent = label.parentElement;
      parent.querySelectorAll(".option-pill").forEach(p => p.classList.remove("selected"));
      label.classList.add("selected");
      radio.checked = true;
      selectedQualityOrFormat = id;
    });

    return label;
  }

  // Tab switching logic
  function switchTab(tabKey) {
    activeTab = tabKey;
    [tabVideo, tabAudio, tabImage].forEach(t => t.classList.remove("active"));
    [paneVideo, paneAudio, paneImage].forEach(p => p.classList.add("hidden"));

    if (tabKey === "video") {
      tabVideo.classList.add("active");
      paneVideo.classList.remove("hidden");
      const sel = paneVideo.querySelector(".option-pill.selected") || paneVideo.querySelector(".option-pill");
      if (sel) {
        sel.classList.add("selected");
        selectedQualityOrFormat = sel.dataset.id;
      }
    } else if (tabKey === "audio") {
      tabAudio.classList.add("active");
      paneAudio.classList.remove("hidden");
      const sel = paneAudio.querySelector(".option-pill.selected") || paneAudio.querySelector(".option-pill");
      if (sel) {
        sel.classList.add("selected");
        selectedQualityOrFormat = sel.dataset.id;
      }
    } else if (tabKey === "image") {
      tabImage.classList.add("active");
      paneImage.classList.remove("hidden");
      const sel = paneImage.querySelector(".option-pill.selected") || paneImage.querySelector(".option-pill");
      if (sel) {
        sel.classList.add("selected");
        selectedQualityOrFormat = sel.dataset.id;
      }
    }
  }

  tabVideo.addEventListener("click", () => switchTab("video"));
  tabAudio.addEventListener("click", () => switchTab("audio"));
  tabImage.addEventListener("click", () => switchTab("image"));

  // Download Trigger & Progress Polling
  downloadBtn.addEventListener("click", async () => {
    if (!currentAnalysisData) return;

    hideStatus();
    progressContainer.classList.remove("hidden");
    completedContainer.classList.add("hidden");
    downloadBtn.disabled = true;
    downloadBtnSpinner.classList.remove("hidden");
    downloadBtnText.textContent = "PREPARING...";

    progressBarFill.style.width = "0%";
    progressPercent.textContent = "0%";
    progressStage.textContent = "Connecting to source...";
    progressSpeed.textContent = "0.0 MB/s";
    progressSize.textContent = "0 MB / 0 MB";

    try {
      const payload = {
        url: urlInput.value.trim(),
        title: currentAnalysisData.title || "download",
        media_type: activeTab,
        quality_or_format: selectedQualityOrFormat,
        extra_data: {
          thumbnail: currentAnalysisData.thumbnail,
          items: currentAnalysisData.items || [],
          direct_download_url: currentAnalysisData.direct_download_url
        }
      };

      const startRes = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const startData = await startRes.json();
      if (!startRes.ok || !startData.success) {
        throw new Error(startData.error || "Failed to initialize download.");
      }

      const jobId = startData.job_id;
      pollJobProgress(jobId);

    } catch (err) {
      showStatus(err.message, "error");
      downloadBtn.disabled = false;
      downloadBtnSpinner.classList.add("hidden");
      downloadBtnText.textContent = "DOWNLOAD";
      progressContainer.classList.add("hidden");
    }
  });

  // Polling Progress Endpoint
  function pollJobProgress(jobId) {
    if (progressInterval) clearInterval(progressInterval);

    progressInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${jobId}`);
        const data = await res.json();

        if (!res.ok || !data.success) {
          clearInterval(progressInterval);
          throw new Error(data.error || "Download tracking failed.");
        }

        const pct = Math.max(0, Math.min(100, Math.round(data.percent || 0)));
        progressBarFill.style.width = `${pct}%`;
        progressPercent.textContent = `${pct}%`;

        if (data.status === "downloading") {
          progressStage.textContent = data.message || "Downloading media...";
          progressSpeed.textContent = data.speed ? `${data.speed} MB/s` : "Receiving stream...";
          const dlStr = formatBytes(data.downloaded_bytes);
          const totStr = data.total_bytes > 0 ? formatBytes(data.total_bytes) : "--";
          progressSize.textContent = `${dlStr} / ${totStr}`;
        } else if (data.status === "processing") {
          progressStage.textContent = data.message || "Processing & converting format...";
          progressSpeed.textContent = "Finalizing...";
        } else if (data.status === "completed") {
          clearInterval(progressInterval);
          progressBarFill.style.width = "100%";
          progressPercent.textContent = "100%";
          progressStage.textContent = "✓ Download complete";
          progressSpeed.textContent = "Ready";

          downloadBtn.disabled = false;
          downloadBtnSpinner.classList.add("hidden");
          downloadBtnText.textContent = "DOWNLOAD AGAIN";

          const fileUrl = `/api/file/${jobId}`;
          saveFileLink.href = fileUrl;
          if (data.filename) {
            saveFileLink.setAttribute("download", data.filename);
            saveFileLink.textContent = `Save ${data.filename} (${formatBytes(data.total_bytes || 0)})`;
          } else {
            saveFileLink.textContent = "Save File to Device";
          }
          completedContainer.classList.remove("hidden");

          // Safely initiate download via iframe without pop-up blocking
          try {
            const dlFrame = document.createElement("iframe");
            dlFrame.style.display = "none";
            dlFrame.src = fileUrl;
            document.body.appendChild(dlFrame);
            setTimeout(() => {
              try { dlFrame.remove(); } catch(e) {}
            }, 60000);
          } catch(e) {
            console.error("Auto-download fallback to save button:", e);
          }
        } else if (data.status === "failed") {
          clearInterval(progressInterval);
          throw new Error(data.error || "The download could not be completed.");
        }

      } catch (err) {
        clearInterval(progressInterval);
        downloadBtn.disabled = false;
        downloadBtnSpinner.classList.add("hidden");
        downloadBtnText.textContent = "DOWNLOAD";
        progressContainer.classList.add("hidden");
        showStatus(err.message, "error");
      }
    }, 600);
  }
});
