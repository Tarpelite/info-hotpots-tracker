import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { askQuestion } from "../api/client.js";
import { getTopDomains } from "../utils/summary.js";

export default function AskBar({ coverage }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const prompts = useMemo(() => {
    const topDomains = getTopDomains(coverage, 3);
    return topDomains.map((item) => `${item.domain} 领域近期有哪些重点团队？`);
  }, [coverage]);

  async function submitAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setError("");
    setAnswer(null);

    try {
      const result = await askQuestion(trimmed);
      if (!result.answer) {
        setError("问答接口没有返回可展示答案。");
      } else {
        setAnswer(result);
      }
    } catch (requestError) {
      setError("问答接口暂不可用。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="ask-console" aria-label="AI4S 问答入口">
      <form className="ask-form" onSubmit={submitAsk}>
        <Sparkles size={18} aria-hidden="true" />
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="问 AI4S 任何问题，回答会附上证据"
          aria-label="输入问题"
        />
        <button type="submit" disabled={submitting || !question.trim()}>
          {/*{submitting ? <Loader2 className="spin" size={17} aria-hidden="true" /> : <ArrowRight size={17} aria-hidden="true" />}*/}
          提问
        </button>
      </form>
      <div className="prompt-row">
        {prompts.map((prompt) => (
          <button
            className="prompt-chip"
            type="button"
            key={prompt}
            onClick={() => setQuestion(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
      {(answer || error) && (
        <div className={answer ? "answer-panel" : "answer-panel muted"}>
          {answer ? (
            <>
              <p>{answer.answer}</p>
              {answer.citations?.length > 0 && (
                <div className="citation-row">
                  {answer.citations.slice(0, 3).map((citation, index) => (
                    <a href={citation.url ?? citation.source_url ?? "#"} key={`${citation.url}-${index}`}>
                      {citation.title ?? citation.source_name ?? `证据 ${index + 1}`}
                    </a>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p>{error}</p>
          )}
        </div>
      )}
    </section>
  );
}
