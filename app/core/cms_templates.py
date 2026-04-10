"""Predefined CMS page templates.

Each template provides:
- id: unique identifier
- name: display name
- description: short description
- category: grouping
- thumbnail: data/asset URL or emoji used in UI
- layout: page layout to use
- content_mode: "html" | "markdown" | "simple"
- content_html: pre-populated HTML body
"""
from typing import Any

PREDEFINED_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "landing",
        "name": "Landing Page",
        "description": "Hero, feature grid, stats, CTA, footer.",
        "category": "marketing",
        "thumbnail": "/assets/templates/landing.svg",
        "layout": "landing",
        "content_mode": "html",
        "content_html": """
<section style=\"padding: 96px 24px; text-align: center; background: linear-gradient(135deg, #111110 0%, #1f1f1e 100%);\">
  <h1 style=\"font-size: 56px; color: #F5F5F5; margin: 0 0 16px; font-weight: 800;\">Your Product Headline</h1>
  <p style=\"font-size: 20px; color: #A1A1AA; max-width: 640px; margin: 0 auto 32px;\">A single sentence that tells visitors why they should care.</p>
  <a href=\"#features\" style=\"background: #F5A623; color: #111110; padding: 14px 32px; border-radius: 10px; font-weight: 600; text-decoration: none; display: inline-block;\">Get Started</a>
</section>

<section id=\"features\" style=\"padding: 72px 24px; max-width: 1100px; margin: 0 auto;\">
  <h2 style=\"font-size: 36px; color: #F5F5F5; text-align: center; margin: 0 0 48px;\">Features</h2>
  <div style=\"display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px;\">
    <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
      <h3 style=\"color: #F5A623; margin: 0 0 8px;\">Fast</h3>
      <p style=\"color: #A1A1AA; margin: 0;\">Describe feature one.</p>
    </div>
    <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
      <h3 style=\"color: #2DD4BF; margin: 0 0 8px;\">Reliable</h3>
      <p style=\"color: #A1A1AA; margin: 0;\">Describe feature two.</p>
    </div>
    <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
      <h3 style=\"color: #F5A623; margin: 0 0 8px;\">Open</h3>
      <p style=\"color: #A1A1AA; margin: 0;\">Describe feature three.</p>
    </div>
  </div>
</section>

<section style=\"padding: 64px 24px; text-align: center; background: rgba(245,166,35,0.05);\">
  <h2 style=\"color: #F5F5F5; font-size: 32px; margin: 0 0 12px;\">Ready to start?</h2>
  <p style=\"color: #A1A1AA; margin: 0 0 24px;\">Join thousands of happy customers.</p>
  <a href=\"#\" style=\"background: #F5A623; color: #111110; padding: 14px 32px; border-radius: 10px; font-weight: 600; text-decoration: none; display: inline-block;\">Sign Up</a>
</section>
""".strip(),
    },
    {
        "id": "about",
        "name": "About Page",
        "description": "Hero, team section, timeline, contact CTA.",
        "category": "company",
        "thumbnail": "/assets/templates/about.svg",
        "layout": "default",
        "content_mode": "html",
        "content_html": """
<h1>About Us</h1>
<p>We build tools that help people understand and automate the physical world.</p>

<h2>Our Team</h2>
<p>We are a small team of engineers, designers, and IoT enthusiasts.</p>

<h2>Our Story</h2>
<ul>
  <li><strong>2023</strong> — Founded with a mission to simplify IoT.</li>
  <li><strong>2024</strong> — Launched our first product.</li>
  <li><strong>2025</strong> — Expanded to multiple countries.</li>
</ul>

<h2>Get in touch</h2>
<p>We'd love to hear from you. <a href=\"/p/contact\">Contact us</a>.</p>
""".strip(),
    },
    {
        "id": "contact",
        "name": "Contact Page",
        "description": "Hero, contact form, map, info.",
        "category": "company",
        "thumbnail": "/assets/templates/contact.svg",
        "layout": "default",
        "content_mode": "html",
        "content_html": """
<h1>Contact Us</h1>
<p>Have a question? Drop us a line below.</p>

<div style=\"margin: 32px 0; padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
  <p style=\"margin: 0 0 12px; color: #A1A1AA;\">Embed a form from the Forms library here, or link to <a href=\"/p/contact-form\">our form page</a>.</p>
</div>

<h2>Our Address</h2>
<p>Musterstraße 1<br/>12345 Musterstadt<br/>Germany</p>

<h2>Email</h2>
<p><a href=\"mailto:hello@example.com\">hello@example.com</a></p>
""".strip(),
    },
    {
        "id": "pricing",
        "name": "Pricing Page",
        "description": "Hero, pricing tiers, FAQ, CTA.",
        "category": "marketing",
        "thumbnail": "/assets/templates/pricing.svg",
        "layout": "landing",
        "content_mode": "html",
        "content_html": """
<section style=\"padding: 72px 24px; text-align: center;\">
  <h1 style=\"font-size: 48px; color: #F5F5F5; margin: 0 0 16px;\">Simple Pricing</h1>
  <p style=\"color: #A1A1AA; font-size: 18px;\">Pick the plan that fits. No hidden fees.</p>
</section>

<section style=\"padding: 32px 24px; max-width: 1100px; margin: 0 auto;\">
  <div style=\"display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px;\">
    <div style=\"padding: 32px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; text-align: center;\">
      <h3 style=\"color: #F5F5F5; margin: 0 0 8px;\">Starter</h3>
      <div style=\"font-size: 40px; color: #F5A623; margin: 16px 0;\">Free</div>
      <ul style=\"color: #A1A1AA; list-style: none; padding: 0;\"><li>Up to 5 devices</li><li>Community support</li></ul>
    </div>
    <div style=\"padding: 32px; background: rgba(245,166,35,0.08); border: 2px solid #F5A623; border-radius: 12px; text-align: center;\">
      <h3 style=\"color: #F5A623; margin: 0 0 8px;\">Pro</h3>
      <div style=\"font-size: 40px; color: #F5A623; margin: 16px 0;\">€29/mo</div>
      <ul style=\"color: #A1A1AA; list-style: none; padding: 0;\"><li>Unlimited devices</li><li>Email support</li><li>Advanced automations</li></ul>
    </div>
    <div style=\"padding: 32px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; text-align: center;\">
      <h3 style=\"color: #F5F5F5; margin: 0 0 8px;\">Enterprise</h3>
      <div style=\"font-size: 40px; color: #2DD4BF; margin: 16px 0;\">Custom</div>
      <ul style=\"color: #A1A1AA; list-style: none; padding: 0;\"><li>Everything in Pro</li><li>SLA</li><li>Dedicated support</li></ul>
    </div>
  </div>
</section>

<section style=\"padding: 72px 24px; max-width: 800px; margin: 0 auto;\">
  <h2 style=\"color: #F5F5F5; text-align: center; margin: 0 0 32px;\">Frequently asked questions</h2>
  <div style=\"margin-bottom: 24px;\">
    <h3 style=\"color: #F5F5F5;\">Can I cancel anytime?</h3>
    <p style=\"color: #A1A1AA;\">Yes, all plans are month-to-month.</p>
  </div>
  <div style=\"margin-bottom: 24px;\">
    <h3 style=\"color: #F5F5F5;\">Do you offer refunds?</h3>
    <p style=\"color: #A1A1AA;\">We offer a 30-day money-back guarantee.</p>
  </div>
</section>
""".strip(),
    },
    {
        "id": "blog_post",
        "name": "Blog Post",
        "description": "Article layout with hero image, text, sidebar.",
        "category": "content",
        "thumbnail": "/assets/templates/blog.svg",
        "layout": "default",
        "content_mode": "markdown",
        "content_html": """
# Your Blog Post Title

*Published {{timestamp:date}} — by Author Name*

![Hero image](https://via.placeholder.com/1200x600)

## Introduction

Write your compelling opening paragraph here. Hook the reader with an interesting angle.

## Main Content

Here you can expand on the topic. Use **bold** for emphasis and *italics* for softer stress. Break ideas into short paragraphs so readers can skim.

### A subsection

- Point one
- Point two
- Point three

## Conclusion

Wrap up with a clear summary and a call-to-action.
""".strip(),
    },
    {
        "id": "docs",
        "name": "Documentation",
        "description": "Documentation layout with sidebar navigation.",
        "category": "content",
        "thumbnail": "/assets/templates/docs.svg",
        "layout": "default",
        "content_mode": "markdown",
        "content_html": """
# Documentation

Welcome to the docs. This page walks through the basics.

## Getting Started

1. Sign in.
2. Connect a device.
3. Create an automation.

## Core Concepts

- **Devices** — physical or virtual things that report data.
- **Variables** — named data points a device sends or receives.
- **Automations** — rules that react to variable changes.

## Next Steps

See the [API reference](/p/api-reference) for a full list of endpoints.
""".strip(),
    },
    {
        "id": "feature",
        "name": "Feature Showcase",
        "description": "Feature showcase with screenshots and descriptions.",
        "category": "marketing",
        "thumbnail": "/assets/templates/feature.svg",
        "layout": "landing",
        "content_mode": "html",
        "content_html": """
<section style=\"padding: 72px 24px; text-align: center; max-width: 900px; margin: 0 auto;\">
  <h1 style=\"font-size: 44px; color: #F5F5F5; margin: 0 0 16px;\">One Tool. Every Possibility.</h1>
  <p style=\"font-size: 18px; color: #A1A1AA;\">An introduction to the feature set that makes our product unique.</p>
</section>

<section style=\"padding: 48px 24px; max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center;\">
  <div>
    <h2 style=\"color: #F5A623;\">Feature One</h2>
    <p style=\"color: #A1A1AA;\">Describe the first feature and why it matters.</p>
  </div>
  <img src=\"https://via.placeholder.com/500x300\" style=\"max-width: 100%; border-radius: 12px;\" />
</section>

<section style=\"padding: 48px 24px; max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center;\">
  <img src=\"https://via.placeholder.com/500x300\" style=\"max-width: 100%; border-radius: 12px;\" />
  <div>
    <h2 style=\"color: #2DD4BF;\">Feature Two</h2>
    <p style=\"color: #A1A1AA;\">Describe the second feature and the problem it solves.</p>
  </div>
</section>
""".strip(),
    },
    {
        "id": "testimonials",
        "name": "Testimonials",
        "description": "Customer testimonials with photos.",
        "category": "marketing",
        "thumbnail": "/assets/templates/testimonials.svg",
        "layout": "default",
        "content_mode": "html",
        "content_html": """
<h1 style=\"text-align: center;\">What our customers say</h1>

<div style=\"display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-top: 32px;\">
  <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
    <p style=\"color: #E5E5E5; font-style: italic;\">&ldquo;This product changed how we work.&rdquo;</p>
    <p style=\"color: #A1A1AA; margin: 12px 0 0;\">— Alex M., CTO</p>
  </div>
  <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
    <p style=\"color: #E5E5E5; font-style: italic;\">&ldquo;Rock-solid and reliable.&rdquo;</p>
    <p style=\"color: #A1A1AA; margin: 12px 0 0;\">— Sara K., Engineer</p>
  </div>
  <div style=\"padding: 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;\">
    <p style=\"color: #E5E5E5; font-style: italic;\">&ldquo;Easy to set up and a joy to use.&rdquo;</p>
    <p style=\"color: #A1A1AA; margin: 12px 0 0;\">— Jamie L., Product Lead</p>
  </div>
</div>
""".strip(),
    },
    {
        "id": "faq",
        "name": "FAQ",
        "description": "Accordion FAQ section.",
        "category": "content",
        "thumbnail": "/assets/templates/faq.svg",
        "layout": "default",
        "content_mode": "html",
        "content_html": """
<h1>Frequently Asked Questions</h1>

<details style=\"margin: 16px 0; padding: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;\">
  <summary style=\"color: #F5F5F5; font-weight: 600; cursor: pointer;\">What is HUBEX?</summary>
  <p style=\"color: #A1A1AA; margin: 12px 0 0;\">HUBEX is a universal IoT device hub.</p>
</details>

<details style=\"margin: 16px 0; padding: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;\">
  <summary style=\"color: #F5F5F5; font-weight: 600; cursor: pointer;\">How much does it cost?</summary>
  <p style=\"color: #A1A1AA; margin: 12px 0 0;\">See our <a href=\"/p/pricing\">pricing page</a> for details.</p>
</details>

<details style=\"margin: 16px 0; padding: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;\">
  <summary style=\"color: #F5F5F5; font-weight: 600; cursor: pointer;\">Is there an API?</summary>
  <p style=\"color: #A1A1AA; margin: 12px 0 0;\">Yes, we have a comprehensive REST API.</p>
</details>
""".strip(),
    },
]


def get_template(template_id: str) -> dict[str, Any] | None:
    for t in PREDEFINED_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "thumbnail": t["thumbnail"],
            "layout": t["layout"],
            "content_mode": t["content_mode"],
        }
        for t in PREDEFINED_TEMPLATES
    ]
