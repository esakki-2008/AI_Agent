import React from "react";

// Public checkout URL. Leave empty until the final Gumroad product URL exists.
// This is a public storefront URL, not a secret.
export const CHECKOUT_URL = import.meta.env.VITE_PURCHASE_URL || "";

export default function PaymentCTA() {
  if (!CHECKOUT_URL) {
    return (
      <section className="payment-cta" aria-label="ClipForge AI purchase">
        <div>
          <span className="payment-eyebrow">CLIPFORGE AI · v1.0.0</span>
          <h2>Ready to create Shorts locally?</h2>
          <p>Get the commercial downloadable package with local AI processing and Windows setup instructions.</p>
        </div>
        <span className="payment-button disabled" aria-disabled="true">Coming soon</span>
      </section>
    );
  }

  return (
    <section className="payment-cta" aria-label="ClipForge AI purchase">
      <div>
        <span className="payment-eyebrow">CLIPFORGE AI · v1.0.0</span>
        <h2>Get the full ClipForge AI package</h2>
        <p>Download the commercial package and start creating Shorts locally with no API subscription.</p>
      </div>
      <a className="payment-button" href={CHECKOUT_URL} target="_blank" rel="noreferrer">Buy ClipForge AI</a>
    </section>
  );
}
