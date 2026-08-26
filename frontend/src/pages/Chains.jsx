import "./ComingSoon.css";

/*
 * Layout placeholder only. Chains do not exist in the backend: there is no
 * pipeline model, no step execution, and no variable substitution. The shapes
 * below are empty on purpose so nothing here can be mistaken for real data.
 */
export default function Chains() {
  return (
    <div className="soon">
      <h1 className="pb-page-title">Chains</h1>
      <p className="soon__note">Prompt chains are in development.</p>

      <div className="soon__frame" aria-hidden="true">
        <div className="soon__pipeline">
          <div className="soon__step">
            <span className="soon__step-dot" />
            <span className="soon__step-line" />
          </div>
          <span className="soon__arrow">&rarr;</span>
          <div className="soon__step">
            <span className="soon__step-dot" />
            <span className="soon__step-line" />
          </div>
          <span className="soon__arrow">&rarr;</span>
          <div className="soon__step">
            <span className="soon__step-dot" />
            <span className="soon__step-line" />
          </div>
          <span className="soon__arrow">&rarr;</span>
          <div className="soon__step soon__step--add" />
        </div>

        <div className="soon__subrow">
          <span className="soon__block soon__chip" />
          <span className="soon__block soon__chip" />
        </div>
      </div>
    </div>
  );
}
