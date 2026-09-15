import React from "react";

// Public Gumroad checkout URL. This is intentionally public, not a secret.
export const CHECKOUT_URL = "https://notebliss.gumroad.com/l/clipforge-ai";

export default function PaymentCTA() {
  return (
    <section className="payment-cta" aria-label="ClipForge AI purchase">
      <div>
        <span className="payment-eyebrow">CLIPFORGE AI · v1.0.0</span>
        <h2>Get the full ClipForge AI package</h2>
        <p>Download the commercial package and start creating Shorts locally with no API subscription.</p>
      </div>
      <a className="payment-button" href={CHECKOUT_URL} target="_blank" rel="noopener noreferrer">Buy ClipForge AI · $19</a>
    </section>
  );
}
