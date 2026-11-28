import './App.css'

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="NexaMind home">
          <span className="brand-mark" aria-hidden="true">N</span>
          <span>NexaMind</span>
        </a>

        <div className="sidebar-section">
          <p className="sidebar-label">Workspace</p>
          <p className="sidebar-empty">
            Your conversations will appear here.
          </p>
        </div>

        <div className="sidebar-footer">
          <span className="status-dot" aria-hidden="true" />
          <span>AI workspace</span>
        </div>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <span className="workspace-context">Workspace</span>
          <span className="workspace-version">NexaMind</span>
        </header>

        <section className="welcome" aria-labelledby="welcome-title">
          <div className="welcome-icon" aria-hidden="true">
            ✳
          </div>

          <p className="eyebrow">YOUR AI WORKSPACE</p>

          <h1 id="welcome-title">
            A clearer space
            <br />
            to think and create.
          </h1>

          <p className="welcome-description">
            Explore ideas, work through problems, and turn your
            thoughts into something meaningful.
          </p>

          <p className="welcome-note">
            Your conversations will start here.
          </p>
        </section>
      </main>
    </div>
  )
}

export default App
