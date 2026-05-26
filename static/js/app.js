const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

function initLoader() {
  const labels = ["Initializing Oxy-Jen Tech...", "Loading futuristic assets...", "Deploying digital experiences..."];
  let step = 0;
  const timer = setInterval(() => {
    $("#loaderText").textContent = labels[step] || labels.at(-1);
    $("#loaderBar").style.width = `${Math.min(100, 18 + step * 38)}%`;
    step += 1;
    if (step > labels.length) {
      clearInterval(timer);
      $("#loader").classList.add("hidden");
    }
  }, 260);
}

function initNav() {
  $("#navToggle")?.addEventListener("click", () => $("#navLinks").classList.toggle("open"));
  const syncThemeLabel = () => {
    const theme = document.documentElement.dataset.theme || "warm";
    $("#themeLabel") && ($("#themeLabel").textContent = theme === "cool" ? "Original" : "Warm");
  };
  syncThemeLabel();
  $("#themeToggle")?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "cool" ? "warm" : "cool";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("oxyTheme", next);
    syncThemeLabel();
    if (window.languageChartInstance) {
      const styles = getComputedStyle(document.documentElement);
      window.languageChartInstance.options.plugins.legend.labels.color = styles.getPropertyValue("--muted");
      window.languageChartInstance.data.datasets[0].backgroundColor = [styles.getPropertyValue("--amber").trim(), styles.getPropertyValue("--amber-2").trim(), styles.getPropertyValue("--ember").trim(), styles.getPropertyValue("--green").trim(), "#f8fbff"];
      window.languageChartInstance.update();
    }
  });
  addEventListener("scroll", () => {
    const total = document.documentElement.scrollHeight - innerHeight;
    $("#scrollLine").style.width = `${total ? (scrollY / total) * 100 : 0}%`;
  });
}

function initSmoothScroll() {
  if (!window.Lenis) return;
  const lenis = new Lenis({ lerp: 0.08, smoothWheel: true });
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const target = link.getAttribute("href");
      if (!target || target === "#") return;
      const node = document.querySelector(target);
      if (!node) return;
      event.preventDefault();
      lenis.scrollTo(node, { offset: -72 });
    });
  });
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
}

function initMotion() {
  if (window.gsap) {
    gsap.registerPlugin(ScrollTrigger);
    gsap.utils.toArray(".reveal").forEach((node) => {
      gsap.to(node, {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: "power3.out",
        scrollTrigger: { trigger: node, start: "top 86%" }
      });
    });
  }
  if ($("#typed")) {
    new Typed("#typed", {
      strings: ["Frontend Developer", "UI Designer", "Full Stack Creator"],
      typeSpeed: 54,
      backSpeed: 26,
      backDelay: 1300,
      loop: true
    });
  }
}

function initTerminal() {
  const code = $("#typedCode");
  if (!code) return;
  const snippet = `$ loading oxy-jen workspace...\n$ syncing project data...\n\nclass OxyJenTech:\n    def __init__(self):\n        self.focus = \"clean web products\"\n        self.stack = [\"Python\", \"Flask\", \"JavaScript\"]\n        self.status = \"building\"\n\n    def build(self):\n        return \"Digital experiences with purpose\"\n\nprint(OxyJenTech().build())`;
  let index = 0;
  let started = false;
  const observer = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting || started) return;
    started = true;
    const timer = setInterval(() => {
      code.textContent = snippet.slice(0, index);
      index += 1;
      if (index > snippet.length) {
        clearInterval(timer);
        if (window.Prism) Prism.highlightElement(code);
      }
    }, 18);
  }, { threshold: 0.35 });
  observer.observe(code);
}

function initCharts() {
  const chart = $("#languageChart");
  if (!chart || !window.Chart) return;
  const data = JSON.parse(chart.dataset.languages || "{}");
  const labels = Object.keys(data);
  const styles = getComputedStyle(document.documentElement);
  window.languageChartInstance = new Chart(chart, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: labels.map((label) => data[label]),
        backgroundColor: [styles.getPropertyValue("--amber").trim(), styles.getPropertyValue("--amber-2").trim(), styles.getPropertyValue("--ember").trim(), styles.getPropertyValue("--green").trim(), "#f8fbff"],
        borderColor: "rgba(255,255,255,.1)"
      }]
    },
    options: { plugins: { legend: { labels: { color: getComputedStyle(document.body).getPropertyValue("--muted") } } }, cutout: "62%" }
  });
}

function initVideos() {
  const videos = $$("video");
  if (!videos.length) return;
  const scrollVideos = videos.filter((video) => (video.dataset.mediaBehavior || "scroll") === "scroll");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => entry.isIntersecting ? entry.target.play().catch(() => {}) : entry.target.pause());
  }, { threshold: 0.45 });
  scrollVideos.forEach((video) => observer.observe(video));
  videos.forEach((video) => {
    const behavior = video.dataset.mediaBehavior || "scroll";
    if (behavior === "cursor") {
      video.pause();
      video.addEventListener("mouseenter", () => video.play().catch(() => {}));
      video.addEventListener("mouseleave", () => video.pause());
    }
    if (behavior === "autoplay") {
      video.play().catch(() => {});
    }
    if (behavior !== "manual") {
      video.addEventListener("mouseenter", () => video.muted = false);
      video.addEventListener("mouseleave", () => video.muted = true);
    }
  });
}

function initProjects() {
  const modal = $("#projectModal");
  if (!modal) return;
  $$(".details-btn").forEach((button) => {
    button.addEventListener("click", () => {
      $("#modalBody").innerHTML = `<h2>${button.dataset.title}</h2><p>${button.dataset.description}</p><p><strong>Language:</strong> ${button.dataset.language}</p><p><strong>Last push:</strong> ${button.dataset.updated}</p>`;
      modal.showModal();
    });
  });
  $("#modalClose").addEventListener("click", () => modal.close());
}

function initProgressAndVotes() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const bar = $(".progress-track i", entry.target);
      if (bar) bar.style.width = `${entry.target.dataset.progress}%`;
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.4 });
  $$(".progress-card").forEach((card) => observer.observe(card));
  $$(".vote-btn").forEach((button, index) => {
    const key = `oxy-challenge-vote-${index}`;
    const value = Number(localStorage.getItem(key) || 0);
    $("span", button).textContent = value;
    button.addEventListener("click", () => {
      const next = Number(localStorage.getItem(key) || 0) + 1;
      localStorage.setItem(key, next);
      $("span", button).textContent = next;
    });
  });
}

function initEditableContent() {
  $$(".typing-text").forEach((node) => {
    const text = node.textContent.trim();
    if (!text || node.dataset.typedReady) return;
    node.dataset.typedReady = "true";
    if (window.Typed) {
      node.textContent = "";
      new Typed(node, { strings: [text], typeSpeed: 42, showCursor: false, loop: false });
    }
  });

  $$("[data-rotating-blocks='true']").forEach((stack) => {
    const blocks = [...stack.children];
    if (blocks.length < 2) return;
    let index = 0;
    blocks.forEach((block, blockIndex) => {
      block.hidden = blockIndex !== 0;
    });
    const rotate = () => {
      const active = blocks[index];
      const displayMs = Number(active.dataset.displaySeconds || 0) * 1000 || 4200;
      const pauseMs = Number(active.dataset.pauseSeconds || 0) * 1000;
      setTimeout(() => {
        active.hidden = true;
        index = (index + 1) % blocks.length;
        blocks[index].hidden = false;
        setTimeout(rotate, pauseMs);
      }, displayMs);
    };
    rotate();
  });

  $$("[data-carousel]").forEach((carousel) => {
    const track = carousel.firstElementChild;
    if (!track) return;
    const display = Number(carousel.dataset.displaySeconds || 0);
    const pause = Number(carousel.dataset.pauseSeconds || 0);
    if (display > 0) {
      const cycle = () => {
        carousel.classList.remove("is-paused");
        setTimeout(() => {
          carousel.classList.add("is-paused");
          setTimeout(cycle, Math.max(0, pause) * 1000);
        }, display * 1000);
      };
      cycle();
    }

    if (carousel.dataset.carouselDirection === "down") {
      track.style.animationDirection = "reverse";
    }

    carousel.addEventListener("mousemove", (event) => {
      const rect = carousel.getBoundingClientRect();
      const ratio = Math.abs((event.clientX - rect.left) / rect.width - 0.5);
      track.style.setProperty("--carousel-duration", `${Math.max(12, 44 - ratio * 48)}s`);
    });

    carousel.addEventListener("wheel", (event) => {
      carousel.classList.add("is-paused");
      carousel.scrollLeft += event.deltaY || event.deltaX;
      clearTimeout(carousel._resumeTimer);
      carousel._resumeTimer = setTimeout(() => carousel.classList.remove("is-paused"), 900);
    }, { passive: true });
  });
}

function initAdminContentPreview() {
  const forms = $$("[data-content-preview-form]");
  const preview = $("[data-content-preview]");
  if (!forms.length || !preview) return;

  const stage = $("[data-preview-stage]", preview);
  const card = $(".preview-card", preview);
  const meta = $("[data-preview-meta]", preview);
  const status = $("[data-preview-status]", preview);
  const title = $("[data-preview-title]", preview);
  const subtitle = $("[data-preview-subtitle]", preview);
  const description = $("[data-preview-description]", preview);
  const media = $("[data-preview-media]", preview);
  const html = $("[data-preview-html]", preview);
  const button = $("[data-preview-button]", preview);
  const pageFrame = $("[data-page-preview-frame]", preview);
  const pageLink = $("[data-page-preview-link]", preview);
  let objectUrls = [];

  let activeForm = forms[0];
  const pageUrls = {
    home: "/",
    about: "/about",
    projects: "/projects",
    ecosystem: "/ecosystem",
    community: "/community",
    contact: "/contact",
    all: "/"
  };

  const value = (form, name) => form.elements[name]?.value?.trim() || "";
  const label = (form, name) => {
    const field = form.elements[name];
    return field?.selectedOptions?.[0]?.textContent || value(form, name);
  };
  const escapeHtml = (text) => text.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const clearObjectUrls = () => {
    objectUrls.forEach((url) => URL.revokeObjectURL(url));
    objectUrls = [];
  };
  const makeMediaNode = (url) => {
    const clean = url.split("?")[0].toLowerCase();
    const isVideo = [".mp4", ".webm", ".ogg", ".mov"].some((ext) => clean.endsWith(ext));
    const node = document.createElement(isVideo ? "video" : "img");
    if (isVideo) {
      node.muted = true;
      node.loop = true;
      node.playsInline = true;
      node.controls = value(activeForm, "media_behavior") === "manual";
      if (value(activeForm, "media_behavior") !== "manual") node.autoplay = true;
    } else {
      node.alt = value(activeForm, "title") || "Preview asset";
    }
    node.src = url;
    return node;
  };

  const update = (form = activeForm) => {
    activeForm = form;
    const layout = value(form, "layout") || "text_block";
    const textEffect = value(form, "text_effect") || "normal";
    const font = value(form, "font_family") || "default";
    const align = value(form, "text_align") || "left";
    const textColor = value(form, "text_color");
    const bg = value(form, "background_url");
    const transparent = form.elements.transparent_bg?.checked;
    const page = value(form, "page") || "home";
    const pageUrl = pageUrls[page] || "/";

    meta.textContent = `${label(form, "page")} · ${label(form, "slot")}`;
    status.textContent = value(form, "status") || label(form, "kind") || "Draft";
    title.textContent = value(form, "title") || "Start typing a title";
    subtitle.textContent = value(form, "subtitle");
    subtitle.hidden = !value(form, "subtitle");
    description.textContent = value(form, "description") || "Your block preview appears here before you save it.";
    html.innerHTML = value(form, "html_content") ? value(form, "html_content") : "";

    button.hidden = !value(form, "button_label") && !value(form, "button_url");
    button.textContent = value(form, "button_label") || "Open";
    button.href = value(form, "button_url") || "#";
    if (pageFrame && pageFrame.getAttribute("src") !== pageUrl) pageFrame.src = pageUrl;
    if (pageLink) pageLink.href = pageUrl;

    stage.style.setProperty("--preview-bg", bg ? `url("${bg}")` : "none");
    card.style.color = textColor || "";
    card.className = `preview-card preview-${layout} effect-${textEffect} font-${font} align-${align}${transparent ? " is-transparent" : ""}`;
    title.classList.toggle("typing-text", textEffect === "typing");
    title.dataset.textEffect = textEffect;

    clearObjectUrls();
    media.innerHTML = "";
    const urls = [];
    const files = [...(form.elements.assets?.files || [])];
    files.forEach((file) => {
      const url = URL.createObjectURL(file);
      objectUrls.push(url);
      urls.push(url);
    });
    if (value(form, "url")) urls.push(value(form, "url"));
    if (value(form, "asset_urls")) urls.push(...value(form, "asset_urls").split(/\r?\n/).map((line) => line.trim()).filter(Boolean));
    urls.slice(0, layout === "infinite_carousel" ? 8 : 1).forEach((url) => media.appendChild(makeMediaNode(url)));

    if (layout === "html_card" && !value(form, "html_content")) {
      html.innerHTML = `<small class="muted">HTML preview will appear here.</small>`;
    }
    if (layout === "rotating_header") {
      description.textContent = `${value(form, "description") || "This header will rotate with other blocks in the same slot."} Display: ${value(form, "display_seconds") || 0}s, pause: ${value(form, "pause_seconds") || 0}s.`;
    }
    if (layout === "infinite_carousel") {
      media.style.animationDirection = ["right", "down"].includes(value(form, "carousel_direction")) ? "reverse" : "normal";
    } else {
      media.style.animationDirection = "";
    }
  };

  forms.forEach((form) => {
    form.addEventListener("focusin", () => update(form));
    form.addEventListener("input", () => update(form));
    form.addEventListener("change", () => update(form));
    const details = form.closest("details");
    details?.addEventListener("toggle", () => {
      if (details.open) {
        update(form);
        preview.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
  update(activeForm);
}

initLoader();
initNav();
initSmoothScroll();
initMotion();
initTerminal();
initCharts();
initVideos();
initProjects();
initProgressAndVotes();
initEditableContent();
initAdminContentPreview();
lucide.createIcons();
