import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import anatomicalHeartImg from '../assets/images/anatomical_heart.png';
import { SYMPTOM_DEFINITIONS } from '../utils/constants';

export default function Home() {
  const navigate = useNavigate();
  const [selectedSymptoms, setSelectedSymptoms] = useState({});

  const toggleSymptom = (id) => {
    setSelectedSymptoms((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const selectedCount = Object.values(selectedSymptoms).filter(Boolean).length;

  const handleStartScreening = () => {
    navigate('/symptom-assessment');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* =========================================================================
          HERO SECTION (Matching User Reference Image 1)
          ========================================================================= */}
      <section style={{
        padding: '3rem 0 5rem',
        backgroundColor: '#ffffff',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div className="app-container" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '3rem',
          alignItems: 'center',
        }}>
          {/* Left Column: Copy & Actions */}
          <div style={{ maxWidth: '620px' }}>
            {/* Pill Badge */}
            <div style={{ marginBottom: '1.25rem' }}>
              <span className="pill-badge">
                <span className="pill-dot" /> AI-POWERED HEART HEALTH SCREENING
              </span>
            </div>

            {/* Main Headline */}
            <h1 style={{
              fontSize: 'clamp(2.6rem, 5vw, 4.3rem)',
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: '-0.04em',
              color: '#0f172a',
              marginBottom: '1.5rem',
            }}>
              Your Heart. Your Health. <span style={{ color: 'var(--primary-red)' }}>A Smarter Way Forward.</span>
            </h1>

            {/* Subtitle */}
            <p style={{
              fontSize: 'clamp(1.05rem, 1.8vw, 1.25rem)',
              color: '#475569',
              lineHeight: 1.55,
              marginBottom: '2.25rem',
            }}>
              Understand your heart health through guided symptom screening, medical information, and AI-supported risk estimates.
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
              <button
                type="button"
                onClick={handleStartScreening}
                className="btn btn-primary btn-lg"
                style={{
                  boxShadow: '0 8px 24px rgba(230, 46, 61, 0.4)',
                }}
              >
                Start Your Screening &rarr;
              </button>

              <a
                href="#how-it-works"
                className="btn btn-secondary btn-lg"
              >
                Explore How It Works
              </a>
            </div>

            {/* Feature Checkpoints */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1.75rem',
              flexWrap: 'wrap',
              fontSize: '0.9rem',
              fontWeight: 600,
              color: '#334155',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <span style={{ color: 'var(--accent-green)' }}>&#10003;</span> Guided symptom screening
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <span style={{ color: 'var(--accent-green)' }}>&#10003;</span> Medical test insights
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <span style={{ color: 'var(--accent-green)' }}>&#10003;</span> Understandable screening results
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual with Glowing Anatomical Heart & Floating Stat Cards */}
          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem 1rem',
          }}>
            {/* Background Radial Glow */}
            <div style={{
              position: 'absolute',
              width: '420px',
              height: '420px',
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(230, 46, 61, 0.08) 0%, rgba(16, 185, 129, 0.06) 50%, transparent 70%)',
              filter: 'blur(30px)',
              zIndex: 0,
            }} />

            {/* 3D Anatomical Heart Image */}
            <img
              src={anatomicalHeartImg}
              alt="CardioCare 3D Anatomical Heart with Bio-luminescent Vascular Visualization"
              style={{
                width: '100%',
                maxWidth: '430px',
                height: 'auto',
                position: 'relative',
                zIndex: 1,
                filter: 'drop-shadow(0 20px 40px rgba(0, 0, 0, 0.12))',
              }}
            />

            {/* Floating Card 1: Heart Rate Demo (Top Left) */}
            <div style={{
              position: 'absolute',
              top: '15%',
              left: '5%',
              zIndex: 2,
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
              padding: '0.75rem 1.25rem',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid #f1f5f9',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.85rem',
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'var(--primary-red-subtle)',
                color: 'var(--primary-red)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-light)', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Heart Rate &bull; Demo
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.1 }}>
                  72 bpm
                </div>
              </div>
            </div>

            {/* Floating Card 2: Blood Pressure Demo (Bottom Right) */}
            <div style={{
              position: 'absolute',
              bottom: '12%',
              right: '5%',
              zIndex: 2,
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              backdropFilter: 'blur(10px)',
              padding: '0.75rem 1.25rem',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid #f1f5f9',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.85rem',
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'var(--accent-green-subtle)',
                color: 'var(--accent-green)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-light)', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Blood Pressure &bull; Demo
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.1 }}>
                  118/76
                </div>
              </div>
            </div>

            {/* Compliance Badge at Bottom Center */}
            <div style={{
              position: 'absolute',
              bottom: '-15px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 3,
            }}>
              <span className="pill-badge pill-badge-green" style={{
                backgroundColor: '#ffffff',
                boxShadow: '0 6px 16px rgba(0, 0, 0, 0.06)',
                padding: '0.55rem 1.25rem',
              }}>
                &#10003; Screening support, not diagnosis
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SYMPTOM CHECK-IN SECTION (Matching User Reference Image 2 & 3)
          ========================================================================= */}
      <section id="symptom-checkin" style={{
        padding: '5rem 0',
        backgroundColor: '#fdfcfb',
      }}>
        <div className="content-container">
          <div style={{ textAlign: 'center', maxWidth: '720px', margin: '0 auto 3rem' }}>
            <span className="pill-badge" style={{ marginBottom: '1rem' }}>
              <span className="pill-dot" /> SYMPTOM CHECK-IN
            </span>
            <h2 style={{
              fontSize: 'clamp(2rem, 3.8vw, 3.2rem)',
              fontWeight: 800,
              color: 'var(--text-main)',
              letterSpacing: '-0.03em',
              marginBottom: '0.85rem',
            }}>
              What Are You Experiencing?
            </h2>
            <p style={{ fontSize: '1.05rem', color: 'var(--text-muted)' }}>
              Select any that apply. This helps guide your screening &mdash; it is not a diagnosis.
            </p>
          </div>

          {/* 6 Symptom Cards Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))',
            gap: '1.25rem',
            marginBottom: '2rem',
          }}>
            {SYMPTOM_DEFINITIONS.map((sym) => {
              const isSelected = Boolean(selectedSymptoms[sym.id]);
              return (
                <div
                  key={sym.id}
                  role="checkbox"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onClick={() => toggleSymptom(sym.id)}
                  onKeyDown={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      toggleSymptom(sym.id);
                    }
                  }}
                  className="clean-card"
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '145px',
                    padding: '1.6rem',
                    borderRadius: 'var(--radius-xl)',
                    backgroundColor: '#ffffff',
                    border: isSelected ? '2px solid var(--primary-red)' : '1px solid #f1f0eb',
                    boxShadow: isSelected ? '0 10px 30px rgba(230, 46, 61, 0.12)' : 'var(--shadow-card)',
                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                    outline: 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '12px',
                      backgroundColor: isSelected ? 'var(--primary-red)' : 'var(--primary-red-subtle)',
                      color: isSelected ? '#ffffff' : 'var(--primary-red)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s ease',
                    }}>
                      {sym.iconType === 'heart-crack' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
                          <path d="m12 13-1-1 2-2-3-3 2-2" />
                        </svg>
                      )}
                      {sym.iconType === 'wind' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
                          <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
                          <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
                        </svg>
                      )}
                      {sym.iconType === 'pulse' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                        </svg>
                      )}
                      {sym.iconType === 'sparkle' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
                        </svg>
                      )}
                      {sym.iconType === 'battery-low' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <rect width="16" height="10" x="2" y="7" rx="2" ry="2" />
                          <line x1="22" x2="22" y1="11" y2="13" />
                          <line x1="6" x2="6" y1="11" y2="13" />
                        </svg>
                      )}
                      {sym.iconType === 'footprint' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M4 16v-2.38C4 11.5 5.79 9.5 8 9.5s4 2 4 4.12V16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
                          <path d="M12 20v-2.38c0-2.12 1.79-4.12 4-4.12s4 2 4 4.12V20a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2Z" />
                        </svg>
                      )}
                    </div>

                    <div style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      border: isSelected ? '2px solid var(--primary-red)' : '2px solid #e5e7eb',
                      backgroundColor: isSelected ? 'var(--primary-red)' : '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ffffff',
                      transition: 'all 0.2s ease',
                    }}>
                      {isSelected && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </div>
                  </div>

                  <div style={{ marginTop: '1.25rem' }}>
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
                      {sym.label}
                    </h3>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Sticky/Bottom Floating Selection Bar matching Screenshot 2 */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#ffffff',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-xl)',
            padding: '1.25rem 2rem',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.04)',
            marginBottom: '1.75rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: selectedCount > 0 ? 'var(--primary-red-subtle)' : '#f3f4f6',
                color: selectedCount > 0 ? 'var(--primary-red)' : 'var(--text-muted)',
                fontWeight: 800,
                fontSize: '0.95rem',
              }}>
                {selectedCount}
              </span>
              <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '1.05rem' }}>
                symptoms selected
              </span>
            </div>

            <button
              type="button"
              onClick={handleStartScreening}
              className="btn btn-primary btn-lg"
              style={{
                padding: '0.85rem 2.2rem',
                boxShadow: '0 6px 20px rgba(230, 46, 61, 0.35)',
              }}
            >
              Continue &rarr;
            </button>
          </div>

          {/* Red Emergency Warning Notice matching Screenshot 3 */}
          <div className="emergency-alert-banner">
            <svg
              className="emergency-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div style={{ fontSize: '0.92rem', lineHeight: '1.5' }}>
              <strong>Emergency notice: </strong>
              If you have severe or persistent chest pain, severe difficulty breathing, fainting, or other potentially life-threatening symptoms, seek emergency medical care immediately. Do not wait for an online screening.
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          HOW IT WORKS SECTION (Matching User Reference Image 3)
          ========================================================================= */}
      <section id="how-it-works" style={{
        padding: '5rem 0',
        backgroundColor: '#ffffff',
      }}>
        <div className="app-container">
          <div style={{ marginBottom: '3rem' }}>
            <span className="pill-badge pill-badge-green" style={{ marginBottom: '1rem' }}>
              <span className="pill-dot" /> HOW IT WORKS
            </span>
            <h2 style={{
              fontSize: 'clamp(2.2rem, 4vw, 3.2rem)',
              fontWeight: 800,
              color: 'var(--text-main)',
              letterSpacing: '-0.03em',
            }}>
              Three steps to clearer insight
            </h2>
          </div>

          {/* Stepped 3 Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '2rem',
          }}>
            {/* Step 01 */}
            <div className="clean-card clean-card-hover" style={{ padding: '2.25rem 2rem' }}>
              <div style={{
                width: '54px',
                height: '54px',
                borderRadius: '16px',
                backgroundColor: 'var(--primary-red)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
                boxShadow: '0 6px 18px var(--primary-red-glow)',
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="8" r="5" />
                  <path d="M20 21a8 8 0 1 0-16 0" />
                </svg>
              </div>

              <div style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '2.5rem',
                fontWeight: 800,
                color: '#fca5a5',
                lineHeight: 1,
                marginBottom: '0.75rem',
              }}>
                01
              </div>

              <h3 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.75rem' }}>
                Share Your Information
              </h3>

              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.55 }}>
                Enter basic health details, relevant medical history, and symptoms.
              </p>
            </div>

            {/* Step 02 */}
            <div className="clean-card clean-card-hover" style={{
              padding: '2.25rem 2rem',
              backgroundColor: '#f2f9f5',
              border: '1px solid #d1fae5',
            }}>
              <div style={{
                width: '54px',
                height: '54px',
                borderRadius: '16px',
                backgroundColor: 'var(--accent-green)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
                boxShadow: '0 6px 18px rgba(16, 185, 129, 0.3)',
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10 2v7.31L4.69 19.34A2 2 0 0 0 6.44 22h11.12a2 2 0 0 0 1.75-2.66L14 9.31V2" />
                  <line x1="8.5" y1="2" x2="15.5" y2="2" />
                  <line x1="14" y1="9.3" x2="10" y2="9.3" />
                </svg>
              </div>

              <div style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '2.5rem',
                fontWeight: 800,
                color: '#86efac',
                lineHeight: 1,
                marginBottom: '0.75rem',
              }}>
                02
              </div>

              <h3 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.75rem' }}>
                Add Medical Test Results
              </h3>

              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.55 }}>
                Provide available measurements and supported medical report values.
              </p>
            </div>

            {/* Step 03 */}
            <div className="clean-card clean-card-hover" style={{
              padding: '2.25rem 2rem',
              backgroundColor: '#fff7f7',
              border: '1px solid #fecaca',
            }}>
              <div style={{
                width: '54px',
                height: '54px',
                borderRadius: '16px',
                backgroundColor: 'var(--primary-red)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
                boxShadow: '0 6px 18px var(--primary-red-glow)',
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 3v18h18" />
                  <path d="m19 9-5 5-4-4-3 3" />
                </svg>
              </div>

              <div style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '2.5rem',
                fontWeight: 800,
                color: '#fca5a5',
                lineHeight: 1,
                marginBottom: '0.75rem',
              }}>
                03
              </div>

              <h3 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.75rem' }}>
                Review Screening Insights
              </h3>

              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.55 }}>
                Explore estimates for supported conditions, missing information, and recommended next steps.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          FEATURES SECTION (Matching Dark Theme in User Reference Image 4)
          ========================================================================= */}
      <section id="features" style={{
        padding: '6rem 0',
        backgroundColor: 'var(--dark-bg)',
        color: '#ffffff',
      }}>
        <div className="app-container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '1.5rem',
            marginBottom: '3.5rem',
          }}>
            <div>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                fontFamily: 'var(--font-heading)',
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.08em',
                padding: '0.4rem 0.95rem',
                borderRadius: 'var(--radius-pill)',
                backgroundColor: 'rgba(230, 46, 61, 0.15)',
                color: '#f87171',
                border: '1px solid rgba(230, 46, 61, 0.3)',
                marginBottom: '1rem',
              }}>
                <span className="pill-dot" /> FEATURES
              </span>
              <h2 style={{
                fontSize: 'clamp(2.4rem, 4vw, 3.4rem)',
                fontWeight: 800,
                color: '#ffffff',
                letterSpacing: '-0.03em',
              }}>
                Built for clarity, not alarm
              </h2>
            </div>

            {/* Subhead Green Pill Notice */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.85rem',
              color: '#34d399',
              padding: '0.6rem 1.15rem',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
            }}>
              <span>&#9432;</span> Estimates are limited to supported conditions and are not a diagnosis.
            </div>
          </div>

          {/* Feature Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem',
          }}>
            {/* Feature 1 */}
            <div style={{
              backgroundColor: 'var(--dark-surface)',
              borderRadius: 'var(--radius-xl)',
              padding: '2.5rem 2rem',
              border: '1px solid var(--dark-border)',
              transition: 'all 0.25s ease',
            }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                backgroundColor: 'var(--primary-red)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="16" height="20" x="4" y="2" rx="2" />
                  <line x1="8" y1="6" x2="16" y2="6" />
                  <line x1="16" y1="14" x2="16" y2="14" />
                  <path d="M16 10h.01" />
                  <path d="M12 10h.01" />
                  <path d="M8 10h.01" />
                  <path d="M12 14h.01" />
                  <path d="M8 14h.01" />
                  <path d="M12 18h.01" />
                  <path d="M8 18h.01" />
                </svg>
              </div>

              <h3 style={{ fontSize: '1.35rem', color: '#ffffff', fontWeight: 800, marginBottom: '0.75rem' }}>
                Guided Symptom Assessment
              </h3>

              <p style={{ color: 'var(--dark-text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                Structured questions help you describe what you're experiencing clearly and consistently using validated Diamond-Forrester criteria.
              </p>
            </div>

            {/* Feature 2 */}
            <div style={{
              backgroundColor: 'var(--dark-surface)',
              borderRadius: 'var(--radius-xl)',
              padding: '2.5rem 2rem',
              border: '1px solid var(--dark-border)',
              transition: 'all 0.25s ease',
            }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                backgroundColor: 'var(--accent-green)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
                  <path d="M14 2v4a2 2 0 0 0 2 2h4" />
                  <path d="M10 9H8" />
                  <path d="M16 13H8" />
                  <path d="M16 17H8" />
                </svg>
              </div>

              <h3 style={{ fontSize: '1.35rem', color: '#ffffff', fontWeight: 800, marginBottom: '0.75rem' }}>
                Medical Report Information
              </h3>

              <p style={{ color: 'var(--dark-text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                Add values from supported medical reports, such as blood pressure or cholesterol results, when available.
              </p>
            </div>

            {/* Feature 3 */}
            <div style={{
              backgroundColor: 'var(--dark-surface)',
              borderRadius: 'var(--radius-xl)',
              padding: '2.5rem 2rem',
              border: '1px solid var(--dark-border)',
              transition: 'all 0.25s ease',
            }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                backgroundColor: 'var(--primary-red)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>

              <h3 style={{ fontSize: '1.35rem', color: '#ffffff', fontWeight: 800, marginBottom: '0.75rem' }}>
                Emergency Rule Primacy
              </h3>

              <p style={{ color: 'var(--dark-text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                Critical red-flag symptoms immediately trigger emergency triage guidance. Low model scores never override emergency safety rules.
              </p>
            </div>

            {/* Feature 4 */}
            <div style={{
              backgroundColor: 'var(--dark-surface)',
              borderRadius: 'var(--radius-xl)',
              padding: '2.5rem 2rem',
              border: '1px solid var(--dark-border)',
              transition: 'all 0.25s ease',
            }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                backgroundColor: 'var(--accent-green)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1.5rem',
              }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
                </svg>
              </div>

              <h3 style={{ fontSize: '1.35rem', color: '#ffffff', fontWeight: 800, marginBottom: '0.75rem' }}>
                Safe Harbor De-identification
              </h3>

              <p style={{ color: 'var(--dark-text-muted)', fontSize: '0.95rem', lineHeight: 1.6 }}>
                Unique pseudonymized patient identifiers and SHA-256 hashed MRNs protect sensitive patient records from plaintext disclosure.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
