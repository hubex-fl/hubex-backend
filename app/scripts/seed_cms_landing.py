"""Seed a default HubEx landing page as a CMS page (if none exists).

The landing page uses slug 'landing' and showcases the 4-level vision:
Connect → Understand → Visualize → Automate.
"""
from datetime import datetime, timezone
import logging

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.cms_page import CmsPage
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")


LANDING_HTML = """<div class="hubex-landing">
  <style>
    .hubex-landing {
      font-family: 'Inter', system-ui, sans-serif;
      color: #E5E5E5;
      background: #111110;
      min-height: 100vh;
      padding: 0;
      margin: 0;
    }
    .hubex-landing * { box-sizing: border-box; }
    .hubex-landing .hero {
      padding: 96px 24px 80px;
      text-align: center;
      background: radial-gradient(ellipse at top, rgba(245,166,35,0.12), transparent 60%);
    }
    .hubex-landing .hero h1 {
      font-family: 'Satoshi', 'Inter', sans-serif;
      font-size: clamp(40px, 6vw, 72px);
      font-weight: 800;
      margin: 0 0 16px;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #F5A623 0%, #2DD4BF 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    .hubex-landing .hero p {
      font-size: clamp(16px, 2vw, 22px);
      color: #A1A1AA;
      max-width: 680px;
      margin: 0 auto 32px;
      line-height: 1.6;
    }
    .hubex-landing .cta-row {
      display: flex;
      gap: 16px;
      justify-content: center;
      flex-wrap: wrap;
    }
    .hubex-landing .btn {
      display: inline-block;
      padding: 14px 28px;
      border-radius: 10px;
      font-weight: 600;
      text-decoration: none;
      font-size: 16px;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .hubex-landing .btn-primary {
      background: #F5A623;
      color: #111110;
      box-shadow: 0 8px 24px rgba(245,166,35,0.32);
    }
    .hubex-landing .btn-primary:hover { transform: translateY(-2px); }
    .hubex-landing .btn-secondary {
      background: transparent;
      color: #2DD4BF;
      border: 1px solid rgba(45,212,191,0.4);
    }
    .hubex-landing .btn-secondary:hover { background: rgba(45,212,191,0.1); }

    .hubex-landing .features {
      max-width: 1200px;
      margin: 0 auto;
      padding: 64px 24px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 24px;
    }
    .hubex-landing .feature-card {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
      padding: 32px 24px;
      transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .hubex-landing .feature-card:hover {
      border-color: rgba(245,166,35,0.4);
      transform: translateY(-4px);
    }
    .hubex-landing .feature-num {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 14px;
      color: #F5A623;
      margin-bottom: 8px;
    }
    .hubex-landing .feature-card h3 {
      font-size: 22px;
      margin: 0 0 12px;
      color: #F5F5F5;
    }
    .hubex-landing .feature-card p {
      margin: 0;
      color: #A1A1AA;
      line-height: 1.6;
      font-size: 15px;
    }

    .hubex-landing .stats {
      max-width: 1000px;
      margin: 0 auto;
      padding: 48px 24px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 32px;
      text-align: center;
      border-top: 1px solid rgba(255,255,255,0.06);
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .hubex-landing .stat-value {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 36px;
      font-weight: 700;
      color: #2DD4BF;
    }
    .hubex-landing .stat-label {
      font-size: 13px;
      color: #71717A;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-top: 4px;
    }

    .hubex-landing .footer {
      padding: 48px 24px;
      text-align: center;
      color: #71717A;
      font-size: 14px;
    }
    .hubex-landing .footer a {
      color: #2DD4BF;
      text-decoration: none;
      margin: 0 12px;
    }
  </style>

  <section class="hero">
    <h1>The Universal IoT Device Hub</h1>
    <p>Connect hardware, services, bridges, and agents. Understand your data. Visualize in real-time. Automate everything.</p>
    <div class="cta-row">
      <a href="/system-stage" class="btn btn-primary">Try the Demo</a>
      <a href="/flow-editor" class="btn btn-secondary">Open System Map</a>
    </div>
  </section>

  <section class="features">
    <div class="feature-card">
      <div class="feature-num">01 · Connect</div>
      <h3>Any device, any protocol</h3>
      <p>Hardware, Services, Bridges, Agents — one unified device model. MQTT, HTTP, WebSocket, CoAP.</p>
    </div>
    <div class="feature-card">
      <div class="feature-num">02 · Understand</div>
      <h3>Semantic types</h3>
      <p>Your data gets meaning. Temperature is temperature — with units, triggers, and conversions.</p>
    </div>
    <div class="feature-card">
      <div class="feature-num">03 · Visualize</div>
      <h3>Dashboards & Maps</h3>
      <p>Drag-drop widgets, real-time streams, interactive 3D System Map for the whole fleet.</p>
    </div>
    <div class="feature-card">
      <div class="feature-num">04 · Automate</div>
      <h3>Rules & Flows</h3>
      <p>IF-THEN automations, visual flow editor, AI copilot. Your hub runs itself.</p>
    </div>
  </section>

  <section class="stats">
    <div>
      <div class="stat-value">{{metric:devices_total}}</div>
      <div class="stat-label">Devices</div>
    </div>
    <div>
      <div class="stat-value">{{metric:devices_online}}</div>
      <div class="stat-label">Online now</div>
    </div>
    <div>
      <div class="stat-value">4</div>
      <div class="stat-label">Abstraction levels</div>
    </div>
  </section>

  <footer class="footer">
    <p>HUBEX — Connect · Understand · Visualize · Automate</p>
    <p>
      <a href="/devices">Devices</a> ·
      <a href="/dashboards">Dashboards</a> ·
      <a href="/flow-editor">System Map</a> ·
      <a href="/tours">Tours</a>
    </p>
    <p style="margin-top:24px; opacity:0.5;">Snapshot: {{timestamp:date}}</p>
  </footer>
</div>
"""


async def seed_landing_page() -> None:
    """Create the default 'landing' CMS page if it doesn't exist."""
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(select(CmsPage).where(CmsPage.slug == "landing"))
            existing = res.scalar_one_or_none()
            if existing:
                logger.info("startup: landing CMS page already present")
                return

            # Pick the first user as owner
            user_res = await db.execute(select(User).order_by(User.id.asc()).limit(1))
            owner = user_res.scalar_one_or_none()
            if not owner:
                logger.info("startup: no users yet, skipping landing seed")
                return

            now = datetime.now(timezone.utc)
            page = CmsPage(
                org_id=getattr(owner, "org_id", None),
                owner_id=owner.id,
                slug="landing",
                title="HUBEX — Universal IoT Device Hub",
                description="Connect, understand, visualize, and automate every device.",
                content_html=LANDING_HTML,
                content_mode="html",
                layout="fullscreen",
                meta_title="HUBEX — The Universal IoT Device Hub",
                meta_description="Connect hardware, services, bridges and agents. Understand your data. Visualize in real-time. Automate everything.",
                visibility="public",
                published=True,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(page)
            await db.commit()
            logger.info("startup: seeded default landing CMS page")
        except Exception as e:
            logger.warning("startup: failed to seed landing CMS page: %s", e)
