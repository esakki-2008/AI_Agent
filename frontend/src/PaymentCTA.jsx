import React from "react";

// Add the public checkout URL here when the product is live.
// Keeping this separate means the storefront can be connected without
// changing the payment UI or application logic later.
export const CHECKOUT_URL = "";

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
