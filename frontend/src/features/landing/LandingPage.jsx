import React, { useState } from 'react';
import { Navbar } from '../../components/layout/Navbar';
import {
  FileText,
  ShieldCheck,
  Users,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Play,
  FileCheck,
  Search,
  Activity,
  Layers,
  Sparkles,
  Lock,
  ChevronDown,
  Building2,
  Eye,
  Check,
  Shield,
  FileSearch,
  Hash,
  Clock,
  Award,
  ExternalLink,
  ChevronRight,
  Database,
  Cpu,
} from 'lucide-react';

export function LandingPage({ onNavigate }) {
  const [activeInspectorDoc, setActiveInspectorDoc] = useState('nba');
  const [activeTab, setActiveTab] = useState('t1');
  const [openFaq, setOpenFaq] = useState(null);

  const toggleFaq = (idx) => {
    setOpenFaq(openFaq === idx ? null : idx);
  };

  // Mock document datasets for live interactive HUD inspector
  const inspectorDocs = {
    nba: {
      id: 'DOC-NBA-2026',
      title: 'NBA Accreditation Certificate',
      institution: 'Demo Engineering College',
      instId: '1-1001',
      programme: 'B.Tech Computer Science & Eng.',
      intake: '120 Approved Seats',
      validity: '2026 – 2029 (Tier-1)',
      ocrConfidence: '99.4%',
      registryStatus: 'Verified (NBA Central Portal)',
      registryColor: 'badge-green',
      ruleResult: 'APH Clause 4.2: COMPLIANT',
      ruleColor: 'var(--green-700)',
      digitalSign: 'Valid X.509 Certificate (Gov of India CCA)',
      statusBadge: 'Preliminary Pass',
      badgeClass: 'badge-green',
    },
    land: {
      id: 'DOC-LND-8821',
      title: 'Government Land Ownership NOC',
      institution: 'Demo Engineering College',
      instId: '1-1001',
      programme: 'Campus Infrastructure (Plot 44/A)',
      intake: '5.2 Acres (Contiguous)',
      validity: 'Perpetual Institutional Use',
      ocrConfidence: '98.1%',
      registryStatus: 'Verified (State Revenue Dept)',
      registryColor: 'badge-green',
      ruleResult: 'APH Clause 6.1: COMPLIANT (>= 5.0 Acres)',
      ruleColor: 'var(--green-700)',
      digitalSign: 'State e-Governance Digital Stamp',
      statusBadge: 'Preliminary Pass',
      badgeClass: 'badge-green',
    },
    infra: {
      id: 'DOC-INF-0932',
      title: 'Building Plan & Fire Safety Audit',
      institution: 'Demo Engineering College',
      instId: '1-1001',
      programme: 'Academic Block B & Labs',
      intake: 'Built-up: 12,400 sq.m',
      validity: 'Expiring in 45 Days',
      ocrConfidence: '94.6%',
      registryStatus: 'Needs Officer Review (Renewal in Progress)',
      registryColor: 'badge-amber',
      ruleResult: 'APH Clause 7.3: ATTENTION (Near Expiry)',
      ruleColor: 'var(--amber-700)',
      digitalSign: 'Municipal Town Planning Stamp',
      statusBadge: 'Review Required',
      badgeClass: 'badge-amber',
    },
  };

  const currentDoc = inspectorDocs[activeInspectorDoc];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg-canvas)' }}>
      <Navbar onNavigate={onNavigate} />

      {/* TOP ANNOUNCEMENT / STATUS STRIP */}
      <div style={{
        backgroundColor: '#fbf4ea',
        borderBottom: '1px solid var(--border-main)',
        padding: '8px 24px',
        fontSize: '12px',
        color: 'var(--ink-secondary)',
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="pulse-dot" />
            <span style={{ fontWeight: 700, color: 'var(--brand-700)' }}>AICTE Approval Process Handbook (APH 2024–2027) Engine Active</span>
            <span style={{ color: 'var(--border-strong)' }}>·</span>
            <span style={{ color: 'var(--ink-muted)' }}>Cryptographic SHA-256 Audit Chain Enforced</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '11.5px', color: 'var(--ink-muted)' }}>
            <span>Dual-Engine OCR: Tesseract + Layout Parser</span>
            <span style={{
              padding: '2px 8px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border-main)',
              fontWeight: 700,
              color: 'var(--brand-700)',
            }}>
              v2.4
            </span>
          </div>
        </div>
      </div>

      {/* HERO SECTION */}
      <section className="hero-bg tech-grid" style={{
        position: 'relative',
        padding: '72px 24px 84px',
        borderBottom: '1px solid var(--border-main)',
        overflow: 'hidden',
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '56px', alignItems: 'center' }}>
          
          {/* Left Column: Value Prop & CTAs */}
          <div style={{ maxWidth: '620px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              backgroundColor: 'rgba(217, 119, 54, 0.08)',
              border: '1px solid rgba(217, 119, 54, 0.25)',
              borderRadius: 'var(--radius-full)',
              marginBottom: '20px',
            }}>
              <Sparkles size={14} style={{ color: 'var(--brand-600)' }} />
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-700)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                National Regulatory Scrutiny Engine
              </span>
            </div>

            <h1 className="font-editorial" style={{ fontSize: '3.4rem', lineHeight: '1.1', fontWeight: 800, margin: '0 0 22px', letterSpacing: '-0.025em' }}>
              <span style={{ color: 'var(--ink)', display: 'block' }}>Trust every application.</span>
              <span className="grad-text" style={{ display: 'block' }}>Authenticate every proof.</span>
            </h1>

            <p style={{ fontSize: '1.12rem', lineHeight: '1.68', color: 'var(--ink-secondary)', marginBottom: '32px' }}>
              Vidya-Niriksha brings computer vision, page-level OCR confidence, and automated Approval Process Handbook validation to educational compliance. Eliminate paper bottlenecks, flag regulatory anomalies, and guarantee tamper-proof audit trails.
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', alignItems: 'center', marginBottom: '36px' }}>
              <button
                onClick={() => onNavigate('/login')}
                className="btn btn-primary"
                style={{ padding: '14px 30px', fontSize: '15px', fontWeight: 700, borderRadius: 'var(--radius-md)' }}
              >
                Explore Platform <ArrowRight size={17} />
              </button>
              <a
                href="#interactive-inspector"
                className="btn btn-secondary"
                style={{ padding: '14px 26px', fontSize: '15px', fontWeight: 600, borderRadius: 'var(--radius-md)' }}
              >
                Inspect Live HUD <Activity size={16} />
              </a>
            </div>

            {/* Feature Pills */}
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '16px',
              paddingTop: '20px',
              borderTop: '1px solid rgba(214, 206, 191, 0.6)',
              fontSize: '12.5px',
              color: 'var(--ink-muted)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--green-600)' }} />
                <span>Zero Hallucinations (Strict OCR)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--green-600)' }} />
                <span>SHA-256 Chained Audit Trail</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--green-600)' }} />
                <span>Human-in-the-Loop Safeguards</span>
              </div>
            </div>
          </div>

          {/* Right Column: Live Interactive Scrutiny HUD */}
          <div id="interactive-inspector" style={{ display: 'flex', justifyContent: 'center' }}>
            <div className="glass-card" style={{
              width: '100%',
              maxWidth: '680px',
              borderRadius: '20px',
              boxShadow: 'var(--shadow-lift)',
              border: '1px solid var(--border-strong)',
              overflow: 'hidden',
              backgroundColor: '#ffffff',
            }}>
              {/* Window Header */}
              <div style={{
                height: '48px',
                borderBottom: '1px solid var(--border-main)',
                backgroundColor: '#fbf9f5',
                padding: '0 18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#ef4444' }}></span>
                  <span style={{ width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#f59e0b' }}></span>
                  <span style={{ width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
                  <span style={{ marginLeft: '12px', fontSize: '12.5px', fontWeight: 800, color: 'var(--ink)' }}>
                    AICTE-APP-2026-00456 · Live Scrutiny Inspector
                  </span>
                </div>
                <span className={`badge ${currentDoc.badgeClass}`} style={{ fontSize: '11px', fontWeight: 700 }}>
                  {currentDoc.statusBadge}
                </span>
              </div>

              {/* Document Switcher Toolbar */}
              <div style={{
                padding: '10px 16px',
                backgroundColor: '#faf6f0',
                borderBottom: '1px solid var(--border-main)',
                display: 'flex',
                gap: '8px',
                overflowX: 'auto',
              }}>
                {[
                  { key: 'nba', label: '1. NBA Accreditation', icon: Award },
                  { key: 'land', label: '2. Land Title NOC', icon: Building2 },
                  { key: 'infra', label: '3. Building Safety Plan', icon: FileCheck },
                ].map((doc) => {
                  const Icon = doc.icon;
                  const isSel = activeInspectorDoc === doc.key;
                  return (
                    <button
                      key={doc.key}
                      onClick={() => setActiveInspectorDoc(doc.key)}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: 'var(--radius-full)',
                        fontSize: '11.5px',
                        fontWeight: isSel ? 700 : 500,
                        backgroundColor: isSel ? 'var(--brand-600)' : '#ffffff',
                        color: isSel ? '#ffffff' : 'var(--ink-secondary)',
                        border: isSel ? '1px solid var(--brand-700)' : '1px solid var(--border-main)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <Icon size={13} />
                      <span>{doc.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Interactive Inspector Content */}
              <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', backgroundColor: '#faf8f5' }}>
                
                {/* Left Pane: Simulated Document Scan with Scan Line */}
                <div style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '12px',
                  border: '1px solid var(--border-main)',
                  padding: '16px',
                  position: 'relative',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  minHeight: '230px',
                }}>
                  <div className="scan-line" />

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--brand-700)', letterSpacing: '0.06em' }}>
                        Original Evidence Scan
                      </span>
                      <span className="badge badge-sky" style={{ fontSize: '9.5px', padding: '2px 6px' }}>
                        {currentDoc.id}
                      </span>
                    </div>

                    <div style={{
                      backgroundColor: '#fdfbf7',
                      border: '1px dashed var(--brand-300)',
                      borderRadius: '8px',
                      padding: '12px',
                      textAlign: 'center',
                      position: 'relative',
                    }}>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--ink)' }}>
                        {currentDoc.title}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--ink-muted)', fontStyle: 'italic', marginTop: '2px' }}>
                        Government of India Regulatory Standing
                      </div>

                      <div style={{
                        marginTop: '10px',
                        padding: '8px',
                        backgroundColor: '#ffffff',
                        borderRadius: '6px',
                        fontSize: '10px',
                        textAlign: 'left',
                        lineHeight: '1.45',
                        border: '1px solid var(--border-subtle)',
                      }}>
                        <div><b>Inst:</b> {currentDoc.institution}</div>
                        <div><b>ID:</b> {currentDoc.instId}</div>
                        <div><b>Scope:</b> {currentDoc.intake}</div>
                        <div><b>Term:</b> {currentDoc.validity}</div>
                      </div>
                    </div>
                  </div>

                  <div style={{
                    marginTop: '12px',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    backgroundColor: 'var(--brand-50)',
                    fontSize: '10px',
                    color: 'var(--brand-800)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}>
                    <Lock size={12} style={{ color: 'var(--brand-600)' }} />
                    <span>{currentDoc.digitalSign}</span>
                  </div>
                </div>

                {/* Right Pane: OCR Extraction & Registry Verification */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  
                  {/* OCR Extraction Box */}
                  <div style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid var(--border-main)',
                    padding: '14px',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
                        Extracted Fields (OCR)
                      </span>
                      <span style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--green-700)' }}>
                        {currentDoc.ocrConfidence} Match
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f4f0e9', paddingBottom: '4px' }}>
                        <span style={{ color: 'var(--ink-muted)' }}>Programme</span>
                        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{currentDoc.programme}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f4f0e9', paddingBottom: '4px' }}>
                        <span style={{ color: 'var(--ink-muted)' }}>Validity</span>
                        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{currentDoc.validity}</span>
                      </div>
                    </div>
                  </div>

                  {/* Registry Verification Box */}
                  <div style={{
                    backgroundColor: '#ffffff',
                    borderRadius: '12px',
                    border: '1px solid var(--border-main)',
                    padding: '14px',
                  }}>
                    <div style={{ fontSize: '10.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: '8px' }}>
                      Registry Verification & Rule Engine
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--ink-muted)' }}>Issuer Registry:</span>
                        <span className={`badge ${currentDoc.registryColor}`} style={{ fontSize: '10px' }}>
                          {currentDoc.registryStatus}
                        </span>
                      </div>
                      <div style={{
                        padding: '6px 8px',
                        borderRadius: '6px',
                        backgroundColor: '#f8f5ee',
                        fontSize: '10.5px',
                        fontWeight: 700,
                        color: currentDoc.ruleColor,
                      }}>
                        {currentDoc.ruleResult}
                      </div>
                    </div>
                  </div>

                </div>

              </div>

              {/* HUD Footer */}
              <div style={{
                padding: '12px 20px',
                borderTop: '1px solid var(--border-main)',
                backgroundColor: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '11.5px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--ink-muted)' }}>
                  <Shield size={14} style={{ color: 'var(--brand-600)' }} />
                  <span>Audit Timestamp: {new Date().toISOString().slice(0, 10)} 08:30 UTC</span>
                </div>
                <button
                  onClick={() => onNavigate('/login')}
                  className="btn btn-outline btn-sm"
                  style={{ fontSize: '11.5px', padding: '4px 10px' }}
                >
                  Open Full Case Dossier <ChevronRight size={13} />
                </button>
              </div>

            </div>
          </div>

        </div>
      </section>

      {/* STATS & IMPACT METRICS STRIP */}
      <section style={{ backgroundColor: '#ffffff', borderBottom: '1px solid var(--border-main)', padding: '44px 24px' }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '28px',
        }}>
          {[
            {
              stat: '99.2%',
              label: 'OCR Extraction Precision',
              desc: 'Dual-engine Tesseract + layout parser with bounding-box confidence.',
              icon: FileSearch,
            },
            {
              stat: '< 4.5s',
              label: 'Automated Dossier Audit',
              desc: 'Transforms 14-day manual intake scrutiny into sub-5-second validation.',
              icon: Clock,
            },
            {
              stat: '42+',
              label: 'AICTE Handbook Rules',
              desc: 'Version-locked rules checking land, intake, faculty, and approvals.',
              icon: Award,
            },
            {
              stat: '100%',
              label: 'Cryptographic Chain of Custody',
              desc: 'Every review and override is sealed into an immutable SHA-256 hash chain.',
              icon: Hash,
            },
          ].map((m, idx) => {
            const Icon = m.icon;
            return (
              <div key={idx} style={{
                padding: '24px',
                borderRadius: 'var(--radius-lg)',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-main)',
                transition: 'var(--transition)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <div className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--brand-700)', lineHeight: 1 }}>
                    {m.stat}
                  </div>
                  <div style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--brand-50)',
                    color: 'var(--brand-600)',
                    display: 'grid',
                    placeItems: 'center',
                  }}>
                    <Icon size={18} />
                  </div>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)', marginBottom: '6px' }}>
                  {m.label}
                </div>
                <div style={{ fontSize: '13px', color: 'var(--ink-muted)', lineHeight: '1.55' }}>
                  {m.desc}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* CORE CAPABILITIES & ARCHITECTURE */}
      <section id="capabilities" style={{ padding: '88px 24px', backgroundColor: 'var(--bg-canvas)' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '24px', marginBottom: '48px' }}>
            <div>
              <span className="eyebrow">A Complete Regulatory Architecture</span>
              <h2 className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, marginTop: '8px' }}>
                Four Pillars of Trust & Verification
              </h2>
            </div>
            <p style={{ maxWidth: '520px', color: 'var(--ink-secondary)', fontSize: '15.5px', lineHeight: '1.65' }}>
              Designed around the real AICTE Approval Process Handbook, Vidya-Niriksha bridges optical document intelligence with institutional governance.
            </p>
          </div>

          {/* 4 Feature Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '24px', marginBottom: '56px' }}>
            <div className="card card-lift" style={{ padding: '30px', backgroundColor: '#ffffff' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'var(--brand-50)', color: 'var(--brand-600)', display: 'grid', placeItems: 'center', marginBottom: '20px' }}>
                <FileText size={24} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '10px', color: 'var(--ink)' }}>
                Multimodal OCR & Layout Intelligence
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.65' }}>
                Extract certificate IDs, dates, programme allotments, and approved seats from scanned PDFs with page-level confidence scores and exact bounding-box coordinates.
              </p>
            </div>

            <div className="card card-lift" style={{ padding: '30px', backgroundColor: '#ffffff' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'var(--brand-50)', color: 'var(--brand-600)', display: 'grid', placeItems: 'center', marginBottom: '20px' }}>
                <ShieldCheck size={24} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '10px', color: 'var(--ink)' }}>
                Approval Handbook Rules Engine
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.65' }}>
                Evaluates mandatory evidence completeness, institutional land eligibility, programme intake thresholds, and certificate validity against versioned AICTE rulebooks.
              </p>
            </div>

            <div className="card card-lift" style={{ padding: '30px', backgroundColor: '#ffffff' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'var(--brand-50)', color: 'var(--brand-600)', display: 'grid', placeItems: 'center', marginBottom: '20px' }}>
                <Database size={24} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '10px', color: 'var(--ink)' }}>
                Authoritative Registry Cross-Check
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.65' }}>
                Queries official issuer databases including NBA accreditation registers, State Land NOC authorities, and university records with built-in SSRF request isolation.
              </p>
            </div>

            <div className="card card-lift" style={{ padding: '30px', backgroundColor: '#ffffff' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'var(--brand-50)', color: 'var(--brand-600)', display: 'grid', placeItems: 'center', marginBottom: '20px' }}>
                <Lock size={24} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '10px', color: 'var(--ink)' }}>
                Tamper-Proof Audit Chain
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.65' }}>
                Every human decision, OCR correction, and rule override is cryptographically linked with previous hashes. Any database tampering immediately invalidates the audit chain.
              </p>
            </div>
          </div>

          {/* Detailed Tabbed Deep Dive */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '24px' }}>
            {[
              { id: 't1', label: 'Rule Execution & Handbook Evaluation' },
              { id: 't2', label: 'Perceptual Image Hashing & Duplication' },
              { id: 't3', label: 'Cryptographic Audit Verification' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-secondary'}`}
                style={{ borderRadius: 'var(--radius-full)', fontSize: '13.5px', padding: '9px 18px' }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="card" style={{ padding: '36px', backgroundColor: '#ffffff' }}>
            {activeTab === 't1' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px', alignItems: 'center' }}>
                <div>
                  <h3 className="font-editorial" style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '14px' }}>
                    Automated Compliance with Clause Citations
                  </h3>
                  <p style={{ fontSize: '15px', color: 'var(--ink-secondary)', lineHeight: '1.7', marginBottom: '16px' }}>
                    Rules are versioned and stored in the database with active regulatory windows. When an application is analyzed, the engine maps uploaded documents directly to AICTE requirements. Every discrepancy includes a cited handbook clause for transparent legal grounding.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '13px', color: 'var(--brand-700)', fontWeight: 600 }}>
                    <span>✓ Clause 4.2 NBA Tier-1 Requirements</span>
                    <span>✓ Clause 6.1 Contiguous Land Norms</span>
                  </div>
                </div>
                <div style={{ background: '#f7f4ee', borderRadius: '12px', padding: '22px', fontFamily: 'var(--font-mono)', fontSize: '12.5px', border: '1px solid var(--border-main)' }}>
                  <div style={{ color: 'var(--brand-700)', fontWeight: 700, marginBottom: '10px' }}>// RULE EVALUATION ENGINE OUTPUT</div>
                  <div><b>Rule ID:</b> R-EOA-DOC-01 (v1.0)</div>
                  <div><b>Category:</b> Mandatory Accreditation</div>
                  <div><b>Target Field:</b> eoa_prior_approval</div>
                  <div><b>Clause:</b> AICTE APH 2024-27 Sec. 3.4</div>
                  <div style={{ color: 'var(--green-700)', marginTop: '8px', fontWeight: 700 }}>
                    Result: PASS (Valid until 30-Jun-2029)
                  </div>
                </div>
              </div>
            )}

            {activeTab === 't2' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px', alignItems: 'center' }}>
                <div>
                  <h3 className="font-editorial" style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '14px' }}>
                    Detecting Duplicate Infrastructure Photos
                  </h3>
                  <p style={{ fontSize: '15px', color: 'var(--ink-secondary)', lineHeight: '1.7', marginBottom: '16px' }}>
                    Unscrupulous applicants sometimes reuse laboratory or campus facility photographs across different college applications. Vidya-Niriksha calculates perceptual image hashes (pHash) and SHA-256 image signatures to instantly flag duplicate submissions.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '13px', color: 'var(--amber-700)', fontWeight: 600 }}>
                    <span>✓ Perceptual Hash Distance &lt; 5</span>
                    <span>✓ Blur & Resolution Checks</span>
                  </div>
                </div>
                <div style={{ background: '#f7f4ee', borderRadius: '12px', padding: '22px', fontFamily: 'var(--font-mono)', fontSize: '12.5px', border: '1px solid var(--border-main)' }}>
                  <div style={{ color: 'var(--amber-700)', fontWeight: 700, marginBottom: '10px' }}>// CROSS-INSTITUTION REUSE DETECTOR</div>
                  <div><b>File:</b> computer_lab_block_a.jpg</div>
                  <div><b>Hash:</b> d41d8cd98f00b204e9800998ecf8427e</div>
                  <div><b>Hamming Distance:</b> 2 (Near Identical)</div>
                  <div style={{ color: 'var(--red-700)', marginTop: '8px', fontWeight: 700 }}>
                    Warning: Matches APP-2025-0012 (Another Institute)
                  </div>
                </div>
              </div>
            )}

            {activeTab === 't3' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px', alignItems: 'center' }}>
                <div>
                  <h3 className="font-editorial" style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '14px' }}>
                    Mathematical Verification of Decisions
                  </h3>
                  <p style={{ fontSize: '15px', color: 'var(--ink-secondary)', lineHeight: '1.7', marginBottom: '16px' }}>
                    Every event — from OCR extraction to officer review decisions and field overrides — contains a SHA-256 hash computed from its timestamp, action payload, and the hash of the preceding event. Any direct SQL manipulation immediately causes verification to fail.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '13px', color: 'var(--sky-700)', fontWeight: 600 }}>
                    <span>✓ Append-Only Event Log</span>
                    <span>✓ One-Click Chain Verification</span>
                  </div>
                </div>
                <div style={{ background: '#f7f4ee', borderRadius: '12px', padding: '22px', fontFamily: 'var(--font-mono)', fontSize: '12.5px', border: '1px solid var(--border-main)' }}>
                  <div style={{ color: 'var(--sky-700)', fontWeight: 700, marginBottom: '10px' }}>// AUDIT CHAIN INTEGRITY CHECK</div>
                  <div><b>Endpoint:</b> /api/v1/admin/audit/verify</div>
                  <div><b>Total Events:</b> 142 Recorded</div>
                  <div><b>Latest Hash:</b> e3b0c44298fc1c149afbf4c8996fb924</div>
                  <div style={{ color: 'var(--green-700)', marginTop: '8px', fontWeight: 700 }}>
                    Chain Status: INTACT (0 Tampered Records)
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </section>

      {/* WORKFLOW PIPELINE: 5 STEPS */}
      <section id="how" style={{ padding: '88px 24px', backgroundColor: '#ffffff', borderTop: '1px solid var(--border-main)' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <span className="eyebrow">End-to-End Scrutiny Flow</span>
            <h2 className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, marginTop: '8px' }}>
              How Applications Move Through SmartVerify
            </h2>
            <p style={{ maxWidth: '640px', margin: '12px auto 0', color: 'var(--ink-muted)', fontSize: '15.5px' }}>
              A standardized, transparent journey that transforms raw application files into evidence-backed regulatory decisions.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
            {[
              {
                step: '01',
                title: 'Intake & Upload',
                desc: 'Institution inputs approved programme details and uploads required PDF and image proofs.',
                icon: FileText,
              },
              {
                step: '02',
                title: 'OCR & Analysis',
                desc: 'Document intelligence extracts fields, checks digital signatures, and reads embedded QR codes.',
                icon: Search,
              },
              {
                step: '03',
                title: 'Rule Assessment',
                desc: 'Versioned compliance checks run against AICTE guidelines, generating evidence-backed findings.',
                icon: FileCheck,
              },
              {
                step: '04',
                title: 'Registry Check',
                desc: 'Authoritative issuers are queried to authenticate certificates and verify accreditation status.',
                icon: Database,
              },
              {
                step: '05',
                title: 'Officer Decision',
                desc: 'Scrutiny and verification officers review findings, record observations, and export audit reports.',
                icon: ShieldCheck,
              },
            ].map((s, idx) => {
              const Icon = s.icon;
              return (
                <div key={idx} className="card card-lift" style={{ padding: '26px 20px', position: 'relative', backgroundColor: 'var(--bg-canvas)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                    <span className="font-mono" style={{ fontSize: '26px', fontWeight: 800, color: 'var(--brand-500)', opacity: 0.85 }}>
                      {s.step}
                    </span>
                    <div style={{
                      width: '34px',
                      height: '34px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--brand-50)',
                      color: 'var(--brand-600)',
                      display: 'grid',
                      placeItems: 'center',
                    }}>
                      <Icon size={16} />
                    </div>
                  </div>
                  <h3 style={{ fontSize: '16.5px', fontWeight: 700, margin: '0 0 8px', color: 'var(--ink)' }}>
                    {s.title}
                  </h3>
                  <p style={{ fontSize: '13px', color: 'var(--ink-muted)', lineHeight: '1.6', margin: 0 }}>
                    {s.desc}
                  </p>
                </div>
              );
            })}
          </div>

        </div>
      </section>

      {/* ROLE-BASED VALUE PROPOSITIONS */}
      <section style={{ padding: '80px 24px', backgroundColor: 'var(--bg-canvas)', borderTop: '1px solid var(--border-main)' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          
          <div style={{ textAlign: 'center', marginBottom: '52px' }}>
            <span className="eyebrow">Designed for Every Stakeholder</span>
            <h2 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '8px' }}>
              Empowering the Regulatory Ecosystem
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '28px' }}>
            
            {/* Institution Card */}
            <div className="card" style={{ padding: '32px', backgroundColor: '#ffffff', borderRadius: '16px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                backgroundColor: 'var(--brand-50)',
                color: 'var(--brand-600)',
                display: 'grid',
                placeItems: 'center',
                marginBottom: '18px',
              }}>
                <Building2 size={22} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--ink)' }}>
                For Institutions & Colleges
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.6', marginBottom: '20px' }}>
                Pre-validate required proofs before final submission. Prevent simple procedural omissions from delaying academic intake approvals.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: 'var(--ink-secondary)' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Instant pre-check against APH requirements
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Clear notice of blurry or unreadable files
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Transparent verification status tracking
                </li>
              </ul>
            </div>

            {/* Scrutiny Officers Card */}
            <div className="card" style={{ padding: '32px', backgroundColor: '#ffffff', borderRadius: '16px', border: '2px solid var(--brand-300)' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                backgroundColor: 'var(--brand-500)',
                color: '#ffffff',
                display: 'grid',
                placeItems: 'center',
                marginBottom: '18px',
              }}>
                <Eye size={22} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--ink)' }}>
                For AICTE Scrutiny Officers
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.6', marginBottom: '20px' }}>
                Review complex application dossiers in minutes instead of hours. Side-by-side OCR bounding overlays highlight discrepancies instantly.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: 'var(--ink-secondary)' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Automated rule-based anomaly detection
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> One-click correction with mandatory audit logs
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Authoritative registry match confirmation
                </li>
              </ul>
            </div>

            {/* Apex Authority Card */}
            <div className="card" style={{ padding: '32px', backgroundColor: '#ffffff', borderRadius: '16px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                backgroundColor: 'var(--brand-50)',
                color: 'var(--brand-600)',
                display: 'grid',
                placeItems: 'center',
                marginBottom: '18px',
              }}>
                <Shield size={22} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px', color: 'var(--ink)' }}>
                For Regional & Apex Committees
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--ink-muted)', lineHeight: '1.6', marginBottom: '20px' }}>
                Access defensible, mathematically verifiable audit trails for hearings, compliance appeals, and judicial inquiries.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: 'var(--ink-secondary)' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Cryptographically chained event verification
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> Exportable PDF & CSV verification summaries
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Check size={14} style={{ color: 'var(--green-600)' }} /> System-wide anomaly trends and risk analytics
                </li>
              </ul>
            </div>

          </div>

        </div>
      </section>

      {/* SAFEGUARDS & RESPONSIBLE AI */}
      <section id="safeguards" style={{ padding: '76px 24px', backgroundColor: '#ffffff', borderTop: '1px solid var(--border-main)' }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
          
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            backgroundColor: 'var(--amber-50)',
            border: '1px solid var(--amber-border)',
            borderRadius: 'var(--radius-full)',
            color: 'var(--amber-700)',
            fontSize: '13px',
            fontWeight: 700,
            marginBottom: '18px',
          }}>
            <Lock size={15} /> Responsible AI & Decision Support Safeguards
          </div>

          <h2 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginBottom: '16px' }}>
            Safe, Transparent & Fully Audited
          </h2>

          <p style={{ fontSize: '16px', color: 'var(--ink-secondary)', lineHeight: '1.7', maxWidth: '820px', margin: '0 auto 40px' }}>
            Vidya-Niriksha does <b>not</b> autonomously approve or reject any educational institution. Every OCR reading is explicitly tagged as machine output, and final regulatory determinations require human officer review recorded in an immutable audit chain.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', textAlign: 'left' }}>
            <div className="card" style={{ padding: '24px', backgroundColor: 'var(--bg-canvas)' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '6px' }}>Document Encryption at Rest</div>
              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', lineHeight: '1.6' }}>
                Files and extracted metadata are secured with AES-256 encryption. Only authorized officers with verified role scopes can access sensitive dossiers.
              </div>
            </div>
            <div className="card" style={{ padding: '24px', backgroundColor: 'var(--bg-canvas)' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '6px' }}>Session & Anti-Tamper Security</div>
              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', lineHeight: '1.6' }}>
                Idempotency keys prevent double submissions, SSRF isolation shields internal services, and epoch tokens enable instant credential revocation.
              </div>
            </div>
            <div className="card" style={{ padding: '24px', backgroundColor: 'var(--bg-canvas)' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '6px' }}>Defensible Legal Export</div>
              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', lineHeight: '1.6' }}>
                One-click compilation of verification certificates and observation logs into structured JSON, CSV, or hearing-ready PDF dossiers.
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* FAQ SECTION */}
      <section id="faq" style={{ padding: '76px 24px', backgroundColor: 'var(--bg-canvas)', borderTop: '1px solid var(--border-main)' }}>
        <div style={{ maxWidth: '860px', margin: '0 auto' }}>
          
          <div style={{ textAlign: 'center', marginBottom: '44px' }}>
            <span className="eyebrow">Frequently Asked Questions</span>
            <h2 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '8px' }}>
              Platform Operations & Governance
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[
              {
                q: 'Can SmartVerify automatically reject an institution application?',
                a: 'No. SmartVerify is strictly a decision-support platform. AI and OCR findings highlight discrepancies and potential missing requirements, but any adverse regulatory action requires human review by an authorized AICTE official.',
              },
              {
                q: 'What document formats are accepted?',
                a: 'The system accepts PDF documents, high-resolution JPEG, and PNG images. For infrastructure evidence, computer vision checks sharpness, blur, and lighting to ensure photographs are legally usable.',
              },
              {
                q: 'How does authoritative source verification work?',
                a: 'The platform integrates with official issuer registries (e.g., NBA Central Registry, State Technical Education Boards, and Land Registration databases) via secure adapters with automated retry and fallback manual recording.',
              },
              {
                q: 'Can scrutiny officers correct misread OCR values?',
                a: 'Yes. Authorized officers can open the Document Viewer, compare the original document image side-by-side with the extracted field, and input a correction with a mandatory audit reason. The rules engine then automatically recalculates compliance.',
              },
              {
                q: 'How does the SHA-256 audit trail prevent tampering?',
                a: 'Each audit event includes the SHA-256 hash of its predecessor. If an unauthorized actor modifies any record directly in the database, the hash chain breaks, which is immediately flagged during system verification.',
              },
            ].map((faq, idx) => (
              <div key={idx} className="card" style={{ padding: '20px 24px', backgroundColor: '#ffffff' }}>
                <div
                  onClick={() => toggleFaq(idx)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', fontWeight: 700, color: 'var(--ink)' }}
                >
                  <span style={{ fontSize: '15px' }}>{faq.q}</span>
                  <ChevronDown
                    size={18}
                    style={{
                      transform: openFaq === idx ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s ease',
                      color: 'var(--brand-600)',
                      flexShrink: 0,
                      marginLeft: '12px',
                    }}
                  />
                </div>
                {openFaq === idx && (
                  <p style={{ marginTop: '14px', fontSize: '14px', color: 'var(--ink-secondary)', lineHeight: '1.65' }}>
                    {faq.a}
                  </p>
                )}
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* HIGH-IMPACT PRE-FOOTER CTA */}
      <section style={{
        padding: '72px 24px',
        backgroundColor: 'var(--brand-900)',
        color: '#ffffff',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at 80% 30%, rgba(217, 119, 54, 0.28) 0%, transparent 60%)',
          pointerEvents: 'none',
        }} />

        <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <span style={{
            display: 'inline-block',
            fontSize: '11px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--amber-400)',
            marginBottom: '16px',
          }}>
            Next-Generation Regulatory Scrutiny
          </span>
          <h2 className="font-editorial" style={{ fontSize: '2.8rem', fontWeight: 800, color: '#ffffff', lineHeight: 1.15, marginBottom: '18px' }}>
            Ready to streamline AICTE institutional scrutiny?
          </h2>
          <p style={{ fontSize: '16px', color: '#d6cebf', lineHeight: '1.7', maxWidth: '680px', margin: '0 auto 36px' }}>
            Empower your institution and scrutiny officers with transparent OCR intelligence, automated handbook compliance, and cryptographic auditability.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigate('/login')}
              className="btn btn-primary"
              style={{ padding: '14px 34px', fontSize: '15px', fontWeight: 700 }}
            >
              Sign In to SmartVerify Platform <ArrowRight size={17} />
            </button>
            <button
              onClick={() => {
                const el = document.getElementById('interactive-inspector');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              className="btn btn-outline"
              style={{
                padding: '14px 28px',
                fontSize: '15px',
                fontWeight: 600,
                color: '#ffffff',
                borderColor: 'rgba(255, 255, 255, 0.3)',
              }}
            >
              Inspect Live Workspace HUD
            </button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="no-print" style={{
        backgroundColor: '#140e0b',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '36px 24px 28px',
        color: '#a8a29e',
        fontSize: '12.5px',
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff', marginBottom: '4px' }}>
              AICTE SmartVerify · <span style={{ color: 'var(--amber-400)' }}>Vidya-Niriksha</span>
            </div>
            <div style={{ fontSize: '11.5px', color: '#78716c' }}>
              National Regulatory Intelligence Platform · Aligned with AICTE APH Standards
            </div>
          </div>

          <div style={{ display: 'flex', gap: '24px', fontSize: '12.5px' }}>
            <a href="#capabilities" style={{ color: '#d6cebf', textDecoration: 'none' }}>Capabilities</a>
            <a href="#how" style={{ color: '#d6cebf', textDecoration: 'none' }}>Workflow</a>
            <a href="#safeguards" style={{ color: '#d6cebf', textDecoration: 'none' }}>Safeguards</a>
            <a href="#faq" style={{ color: '#d6cebf', textDecoration: 'none' }}>FAQ</a>
          </div>
        </div>

        <div style={{ maxWidth: '1400px', margin: '20px auto 0', paddingTop: '18px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', fontSize: '11px', color: '#57534e' }}>
          <div>
            AI outputs are preliminary decision-support recommendations. Final regulatory authority rests with authorized AICTE officers.
          </div>
          <div>
            Synthetic Demo Environment · Not an official AICTE production system
          </div>
        </div>
      </footer>
    </div>
  );
}
