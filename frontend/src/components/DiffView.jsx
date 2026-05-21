import './DiffView.css'

function computeDiff(oldText, newText) {
  const oldWords = oldText.trim().split(/\s+/)
  const newWords = newText.trim().split(/\s+/)

  const dp = Array(oldWords.length + 1)
    .fill(null)
    .map(() => Array(newWords.length + 1).fill(0))

  for (let i = 1; i <= oldWords.length; i++) {
    for (let j = 1; j <= newWords.length; j++) {
      if (oldWords[i - 1] === newWords[j - 1]) {
        dp[i][j] = dp[i-1][j-1] + 1
      } else {
        dp[i][j] = Math.max(dp[i-1][j], dp[i][j-1])
      }
    }
  }

  const result = []
  let i = oldWords.length
  let j = newWords.length

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldWords[i-1] === newWords[j-1]) {
      result.push({ word: oldWords[i-1], type: 'unchanged' })
      i--; j--
    } else if (i > 0 && (j === 0 || dp[i-1][j] >= dp[i][j-1])) {
      result.push({ word: oldWords[i-1], type: 'removed' })
      i--
    } else {
      result.push({ word: newWords[j-1], type: 'added' })
      j--
    }
  }

  return result.reverse()
}

export default function DiffView({ versionA, versionB, totalVersions }) {

  if (totalVersions < 1) {
    return (
      <div className="diff-blocked">
        <p>You need at least one saved version to compare.</p>
      </div>
    )
  }

  const diff = computeDiff(versionA.prompt_text, versionB.prompt_text)

  return (
    <div className="diff-container">

      <div className="diff-column">
        <h3>{versionA.name}</h3>
        <div className="diff-text">
          {diff.filter(chunk => chunk.type !== 'added').map((chunk, index) => (
            <span
              key={index}
              className={chunk.type === 'removed' ? 'diff-removed' : ''}
            >
              {chunk.word}{' '}
            </span>
          ))}
        </div>
        {versionA.response_text && (
          <div className="diff-response">
            <h4>Response</h4>
            <p>{versionA.response_text}</p>
          </div>
        )}
      </div>

      <div className="diff-column">
        <h3>{versionB.name}</h3>
        <div className="diff-text">
          {diff.filter(chunk => chunk.type !== 'removed').map((chunk, index) => (
            <span
              key={index}
              className={chunk.type === 'added' ? 'diff-added' : ''}
            >
              {chunk.word}{' '}
            </span>
          ))}
        </div>
        {versionB.response_text && (
          <div className="diff-response">
            <h4>Response</h4>
            <p>{versionB.response_text}</p>
          </div>
        )}
      </div>

    </div>
  )
}