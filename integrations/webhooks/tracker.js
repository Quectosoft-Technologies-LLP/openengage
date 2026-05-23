/**
 * OpenEngage Web Tracker v1.0
 * Patent-safe: standard UTM + session tracking only.
 * Embed on any website: <script src="https://your-openengage.com/tracker.js" async></script>
 */
(function() {
  const OE_API = "https://your-openengage.com/webhooks/track"; // ← change this

  function getUTMParams() {
    const p = new URLSearchParams(window.location.search);
    return {
      utm_source:   p.get("utm_source")   || "",
      utm_medium:   p.get("utm_medium")   || "",
      utm_campaign: p.get("utm_campaign") || "",
      utm_content:  p.get("utm_content")  || "",
    };
  }

  function getOrCreateSession() {
    let sid = sessionStorage.getItem("oe_session");
    if (!sid) {
      sid = crypto.randomUUID ? crypto.randomUUID()
            : "xxxx-xxxx".replace(/x/g, () => (Math.random()*16|0).toString(16));
      sessionStorage.setItem("oe_session", sid);
    }
    return sid;
  }

  function trackPageView() {
    const payload = {
      session_id:  getOrCreateSession(),
      page_url:    window.location.href,
      page_title:  document.title,
      referrer:    document.referrer,
      email:       localStorage.getItem("oe_contact_email") || null,
      ...getUTMParams(),
    };
    // Store UTM for subsequent pages
    const utms = getUTMParams();
    if (utms.utm_source) localStorage.setItem("oe_utms", JSON.stringify(utms));

    fetch(OE_API, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {}); // silently fail
  }

  // Track form submits and capture email
  function trackForms() {
    document.querySelectorAll("form").forEach(form => {
      form.addEventListener("submit", function() {
        const emailInput = form.querySelector("input[type=email]");
        if (emailInput && emailInput.value) {
          localStorage.setItem("oe_contact_email", emailInput.value);
          fetch(OE_API, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({
              session_id:    getOrCreateSession(),
              page_url:      window.location.href,
              email:         emailInput.value,
              activity_type: "form_submitted",
              form_id:       form.id || form.action,
              ...getUTMParams(),
            }),
            keepalive: true,
          }).catch(() => {});
        }
      });
    });
  }

  // Run on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => { trackPageView(); trackForms(); });
  } else {
    trackPageView();
    trackForms();
  }

  // Single-page app support (React, Vue, etc.)
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      trackPageView();
    }
  }).observe(document, { subtree: true, childList: true });

  // Expose public API
  window.OpenEngage = {
    identify: (email) => {
      localStorage.setItem("oe_contact_email", email);
    },
    track: (event, props = {}) => {
      fetch(OE_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: getOrCreateSession(),
          page_url:   window.location.href,
          email:      localStorage.getItem("oe_contact_email"),
          activity_type: event,
          ...props,
          ...getUTMParams(),
        }),
        keepalive: true,
      }).catch(() => {});
    }
  };
})();
