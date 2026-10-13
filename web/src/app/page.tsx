import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-content">
          <p className="eyebrow">PRELUMA AI · YUNNAN UNIVERSITY</p>
          <h1 id="hero-title">
            Prepare before class.
            <br />
            <span>Understand more during class.</span>
          </h1>
          <p className="hero-lede">
            AI-powered pre-class learning. Brain Brief, adaptive quiz,
            multi-provider tutor and teacher analytics. All in Python.
          </p>
          <Link className="button" href="/courses">
            Explore courses <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>
      <section className="content-section" aria-labelledby="platform-title">
        <div className="section-heading">
          <p className="eyebrow">BUILT FOR THE MOMENT BEFORE CLASS</p>
          <h2 id="platform-title">Everything in one platform</h2>
        </div>
        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-number">01</span>
            <h3>Student Mission</h3>
            <p>
              Move from a quick brief through practice and a mock test, with
              your progress in view.
            </p>
          </article>
          <article className="feature-card">
            <span className="feature-number">02</span>
            <h3>Ask Preluma AI</h3>
            <p>
              Explore grounded answers and source citations, with an offline
              learning path when providers are unavailable.
            </p>
          </article>
          <article className="feature-card">
            <span className="feature-number">03</span>
            <h3>Course insight</h3>
            <p>
              See what you have covered and what deserves attention before the
              next class.
            </p>
          </article>
        </div>
      </section>
    </>
  );
}
