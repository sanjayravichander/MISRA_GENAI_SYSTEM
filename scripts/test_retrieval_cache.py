import json

from app.retrieval.retrieve_rules import retrieve_with_cache


def main():
    payload = {
        "rule_id": "Rule 8.11",
        "warning_message": "External linkage should be declared in one and only one file",
        "code_snippet": """
extern int g_counter;
void foo(void)
{
    g_counter++;
}
""",
        "checker_name": "MISRA2012-RULE-8_11",
        "top_k": 5,
    }

    print("=== First run ===")
    result1 = retrieve_with_cache(**payload)
    print("source:", result1["source"])

    retrieval_result_1 = result1.get("retrieval_result", {})
    matches_1 = retrieval_result_1.get("matches", [])

    if matches_1:
        top = matches_1[0]
        print("top rule:", top.get("guideline_id", "N/A"))
        print("base score:", top.get("score", "N/A"))
        print("reranked score:", top.get("reranked_score", "N/A"))

        print("\n=== TOP MATCH FULL OBJECT ===")
        print(json.dumps(top, indent=2, ensure_ascii=False))
    else:
        print("No retrieval matches found.")

    print("\n=== Second run ===")
    result2 = retrieve_with_cache(**payload)
    print("source:", result2["source"])

    retrieval_result_2 = result2.get("retrieval_result", {})
    matches_2 = retrieval_result_2.get("matches", [])

    if matches_2:
        top = matches_2[0]
        print("top rule:", top.get("guideline_id", "N/A"))
        print("base score:", top.get("score", "N/A"))
        print("reranked score:", top.get("reranked_score", "N/A"))
    else:
        print("No retrieval matches found.")


if __name__ == "__main__":
    main()