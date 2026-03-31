import json

from app.generation.generate_misra_response import (
    GenerationConfig,
    generate_misra_response,
)


def main():
    config = GenerationConfig(
        model_path=r"C:\models\Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        n_ctx=4096,
        n_threads=8,
        n_gpu_layers=0,
        temperature=0.0,
        top_p=1.0,
        top_k=1,
        repeat_penalty=1.0,
        seed=42,
        max_tokens=1400,
        prompt_version="misra_generation_v1",
    )

    result = generate_misra_response(
        rule_id="Rule 8.11",
        warning_message="When an array with external linkage is declared, its size should be explicitly specified",
        code_snippet="""
extern int arr[];
void foo(void)
{
    arr[0] = 1;
}
""",
        checker_name="MISRA2012-RULE-8_11",
        config=config,
        top_k=5,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()