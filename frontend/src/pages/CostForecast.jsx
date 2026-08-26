import "./ComingSoon.css";

/*
 * Layout placeholder only. No cost data exists to show: all three provider
 * adapters discard the SDK usage object, so token counts are never captured
 * and PromptVersion has no cost columns. Every figure here is a blank shape
 * rather than a number.
 */
export default function CostForecast() {
  return (
    <div className="soon">
      <h1 className="pb-page-title">Cost forecast</h1>
      <p className="soon__note">Cost tracking is in development.</p>

      <div className="soon__frame" aria-hidden="true">
        <div className="soon__stats">
          {[0, 1, 2].map((i) => (
            <div className="soon__block soon__stat" key={i}>
              <span className="soon__stat-value" />
              <span className="soon__stat-label" />
            </div>
          ))}
        </div>
      </div>

      <div className="soon__frame" aria-hidden="true">
        <div className="soon__rows">
          {[0, 1, 2].map((i) => (
            <div className="soon__list-row" key={i}>
              <span className="soon__bar soon__bar--wide" />
              <span className="soon__bar soon__bar--mid" />
              <span className="soon__bar soon__bar--narrow" />
            </div>
          ))}
        </div>
      </div>

      <div className="soon__frame" aria-hidden="true">
        <div className="soon__block soon__forecast">
          <span className="soon__bar soon__bar--wide" />
          <span className="soon__bar soon__bar--mid" />
        </div>
      </div>
    </div>
  );
}
