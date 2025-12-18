#!/usr/bin/env python3
"""
交互式测试脚本
分步骤测试 GRE Math Tutor 的各个功能模块

使用方法:
    python scripts/interactive_test.py

或单独测试某个模块:
    python scripts/interactive_test.py pdf      # 测试 PDF 转图片
    python scripts/interactive_test.py extract  # 测试题目抽取
    python scripts/interactive_test.py solve    # 测试求解
    python scripts/interactive_test.py diagnose # 测试诊断
    python scripts/interactive_test.py full     # 完整流程测试
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60 + "\n")

def test_pdf_to_images():
    """测试 PDF 转图片功能"""
    print_header("测试 PDF 转图片 (Stage 0)")
    
    pdf_path = "data/samples/Linear_Equations.pdf"
    
    # 如果 PDF 不存在，先创建
    # if not os.path.exists(pdf_path):
    #     pdf_path = create_sample_pdf()
    #     if not pdf_path:
    #         return None
    
    try:
        from gre_tutor.ingest.pdf_to_images import pdf_to_images, get_pdf_page_count
        
        # 获取页数
        total_pages = get_pdf_page_count(pdf_path)
        print(f"📄 PDF 文件: {pdf_path}")
        print(f"📄 总页数: {total_pages}")
        
        # 转换
        output_dir = "outputs/test_pages"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n正在转换...")
        image_paths = pdf_to_images(
            pdf_path=pdf_path,
            output_dir=output_dir,
            pages="all",
            dpi=200
        )
        
        print(f"\n✅ 转换成功!")
        print(f"   生成 {len(image_paths)} 张图片:")
        for path in image_paths:
            print(f"   - {path}")
        
        return image_paths
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_vision_extract(image_paths=None, use_mock=False):
    """测试视觉抽题功能"""
    print_header("测试视觉抽题 (Stage T)")
    
    # 如果没有提供图片路径，先进行 PDF 转换
    if not image_paths:
        image_paths = test_pdf_to_images()
        if not image_paths:
            return None
    
    print(f"\n📷 待处理图片: {len(image_paths)} 张")
    print(f"🤖 模式: {'Mock (离线测试)' if use_mock else 'OpenAI API'}")
    
    try:
        if use_mock:
            from gre_tutor.llm.mock_client import MockLLMClient
            client = MockLLMClient()
        else:
            from gre_tutor.llm.openai_client import OpenAIClient
            client = OpenAIClient()
            if not client.is_available:
                print("⚠️ OpenAI API Key 未配置，切换到 Mock 模式")
                from gre_tutor.llm.mock_client import MockLLMClient
                client = MockLLMClient()
        
        from gre_tutor.ingest.vision_extract import VisionQuestionExtractor
        
        extractor = VisionQuestionExtractor(client)
        
        print(f"\n正在抽取题目...")
        questions, failed_pages, errors = extractor.extract_from_images(
            image_paths=image_paths,
            pdf_name="Linear_Equations.pdf"
        )
        if errors:
            print("\n❌ 失败详情(前3条):")
        for e in errors[:3]:
            print("-----")
            print(e[:1000])
            if failed_pages:
                print(f"   失败页码: {failed_pages}")
        
        # 显示抽取结果
        print(f"\n📋 抽取结果:")
        for q in questions:
            print(f"\n   [{q.id}] 页码: {q.source.page}")
            print(f"   题干: {q.stem[:60]}{'...' if len(q.stem) > 60 else ''}")
            print(f"   选项: {list(q.choices.keys())}")
            print(f"   置信度: {q.confidence:.2f}")
        
        # 保存结果
        output_file = "outputs/test_transcribed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "questions": [q.model_dump() for q in questions]
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存: {output_file}")
        
        return questions
        
    except Exception as e:
        print(f"❌ 抽取失败: {e}")
        import traceback
        traceback.print_exc()
        return None

from gre_tutor.core.models import Question
def load_questions_from_json(path: str) -> list[Question]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    for q in data["questions"]:
        questions.append(Question.model_validate(q))

    return questions
    

from gre_tutor.core.models import SolveResult

def load_solve_results(path: str) -> list[SolveResult]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [SolveResult.model_validate(r) for r in data["solve_results"]]
def test_solver(questions=None, use_mock=True):
    """测试求解功能"""
    print_header("测试求解 (Stage S)")
    
    # 如果没有题目，先创建测试题目
    if not questions:
        from gre_tutor.core.models import Question, QuestionSource
        questions = [
            Question(
                id="p1_q1",
                source=QuestionSource(pdf="test.pdf", page=1),
                stem="If x + 5 = 12, what is the value of x?",
                choices={"A": "5", "B": "6", "C": "7", "D": "8", "E": "17"}
            ),
            Question(
                id="p1_q2",
                source=QuestionSource(pdf="test.pdf", page=1),
                stem="What is the area of a circle with radius 4?",
                choices={"A": "4π", "B": "8π", "C": "12π", "D": "16π", "E": "64π"}
            )
        ]
        print("📝 使用默认测试题目")
    
    print(f"📝 待求解: {len(questions)} 道题目")
    print(f"🤖 模式: {'Mock (离线测试)' if use_mock else 'OpenAI API'}")
    
    try:
        if use_mock:
            from gre_tutor.llm.mock_client import MockLLMClient
            client = MockLLMClient()
        else:
            from gre_tutor.llm.openai_client import OpenAIClient
            client = OpenAIClient()
            if not client.is_available:
                print("⚠️ OpenAI API Key 未配置，切换到 Mock 模式")
                from gre_tutor.llm.mock_client import MockLLMClient
                client = MockLLMClient()
        
        from gre_tutor.core.solver import QuestionSolver
        
        solver = QuestionSolver(client)
        
        print(f"\n正在求解...")
        results, errors = solver.solve_batch(questions)
        
        print(f"\n✅ 求解完成!")
        print(f"   成功求解: {len(results)} 道题目")
        if errors:
            print("\n❌ 失败详情(前3条):")
            for e in errors[:3]:
                print("-----")
                print(e[:1000])
        
        # 显示求解结果
        print(f"\n📋 求解结果:")
        for r in results:
            print(f"\n   [{r.question_id}]")
            print(f"   正确答案: {r.correct_answer}")
            print(f"   知识点: {r.topic}")
            print(f"   关键步骤:")
            for i, step in enumerate(r.key_steps, 1):
                print(f"      {i}. {step}")
        
        # 保存结果
        output_file = "outputs/test_solve_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "solve_results": [r.model_dump() for r in results]
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存: {output_file}")
        return results
        
    except Exception as e:
        print(f"❌ 求解失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_diagnose(questions=None, solve_results=None, user_answers=None, use_mock=True):
    """测试诊断功能"""
    print_header("测试诊断 (Stage D)")
    
    # 准备测试数据
    if not questions:
        from gre_tutor.core.models import Question, QuestionSource
        questions = [
            Question(
                id="p1_q1",
                source=QuestionSource(pdf="test.pdf", page=1),
                stem="If x + 5 = 12, what is the value of x?",
                choices={"A": "5", "B": "6", "C": "7", "D": "8", "E": "17"}
            ),
            Question(
                id="p1_q2",
                source=QuestionSource(pdf="test.pdf", page=1),
                stem="What is the area of a circle with radius 4?",
                choices={"A": "4π", "B": "8π", "C": "12π", "D": "16π", "E": "64π"}
            )
        ]
    
    if not solve_results:
        from gre_tutor.core.models import SolveResult
        solve_results = [
            SolveResult(
                question_id="p1_q1",
                correct_answer="C",  # x = 7
                topic="algebra",
                key_steps=["从 x + 5 = 12 出发", "两边减 5", "得到 x = 7"],
                final_reason="简单代数运算"
            ),
            SolveResult(
                question_id="p1_q2",
                correct_answer="D",  # 16π
                topic="geometry",
                key_steps=["圆面积公式 A = πr²", "代入 r = 4", "A = 16π"],
                final_reason="套用圆面积公式"
            )
        ]
    
    if not user_answers:
        user_answers = {}
        for idx, r in enumerate(solve_results, start=1):
            if idx % 3 == 0:
                user_answers[r.question_id] = "A"  # 故意错
            else:
                user_answers[r.question_id] = r.correct_answer
    
    print(f"📝 待诊断: {len(questions)} 道题目")
    print(f"📝 用户答案: {user_answers}")
    print(f"🤖 模式: {'Mock (离线测试)' if use_mock else 'OpenAI API'}")
    
    try:
        if use_mock:
            from gre_tutor.llm.mock_client import MockLLMClient
            client = MockLLMClient()
        else:
            from gre_tutor.llm.openai_client import OpenAIClient
            client = OpenAIClient()
            if not client.is_available:
                print("⚠️ OpenAI API Key 未配置，切换到 Mock 模式")
                from gre_tutor.llm.mock_client import MockLLMClient
                client = MockLLMClient()
        
        from gre_tutor.core.diagnose import ErrorDiagnoser
        
        diagnoser = ErrorDiagnoser(client)
        
        print(f"\n正在诊断...")
        results, errors = diagnoser.diagnose_batch(questions, solve_results, user_answers)
        
        print(f"\n✅ 诊断完成!")
        
        # 统计
        correct_count = sum(1 for r in results if r.is_correct)
        print(f"   正确: {correct_count}/{len(results)}")
        
        # 显示诊断结果
        print(f"\n📋 诊断结果:")
        for r in results:
            status = "✅ 正确" if r.is_correct else "❌ 错误"
            print(f"\n   [{r.question_id}] {status}")
            print(f"   用户答案: {r.user_answer} | 正确答案: {r.correct_answer}")
            
            if not r.is_correct:
                print(f"\n   🔍 错因分析:")
                if r.why_user_choice_is_tempting:
                    print(f"      为什么会误选: {r.why_user_choice_is_tempting[:80]}...")
                if r.likely_misconceptions:
                    print(f"      可能的误区:")
                    for m in r.likely_misconceptions:
                        print(f"         - {m}")
                if r.how_to_get_correct:
                    print(f"      如何得到正确答案: {r.how_to_get_correct[:80]}...")
        
        # 保存结果
        output_file = "outputs/test_diagnose_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "diagnose_results": [r.model_dump() for r in results]
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存: {output_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_full_pipeline(use_mock=True):
    """测试完整流程"""
    print_header("完整流程测试")
    
    print("这将执行完整的端到端流程:")
    print("  1. 创建/使用样例 PDF")
    print("  2. PDF 转图片")
    print("  3. 视觉抽题 (Stage T)")
    print("  4. 求解 (Stage S)")
    print("  5. 诊断 (Stage D)")
    print("  6. 生成报告")
    
    print(f"\n🤖 模式: {'Mock (离线测试)' if use_mock else 'OpenAI API'}")
    
    # 检查 PDF
    pdf_path = "data/samples/sample.pdf"
    if not os.path.exists(pdf_path):
        print("\n📄 创建样例 PDF...")
        create_sample_pdf()
    
    try:
        from gre_tutor.core.pipeline import GREMathPipeline
        
        pipeline = GREMathPipeline(
            use_mock=use_mock,
            output_dir="outputs"
        )
        
        # 准备模拟答案（第一题对，第二题错）
        answers_file = "outputs/test_answers.json"
        with open(answers_file, 'w') as f:
            json.dump({"p1_q1": "C", "p1_q2": "A"}, f)
        
        print("\n🚀 开始执行完整流程...\n")
        
        result = pipeline.run(
            pdf_path=pdf_path,
            mode="diagnose",
            pages="all",
            dpi=200,
            answers_json=answers_file
        )
        
        print("\n" + "=" * 60)
        print("✅ 完整流程执行成功!")
        print("=" * 60)
        
        print(f"\n📁 输出目录: outputs/session_{result.session_id}/")
        print(f"   - pages/          # 转换的图片")
        print(f"   - transcribed.json # 抽题结果")
        print(f"   - results.json    # 完整结果")
        print(f"   - report.md       # Markdown 报告")
        print(f"   - logs.txt        # 运行日志")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 流程执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_menu():
    """显示交互菜单"""
    print("\n" + "=" * 60)
    print("🎯 GRE Math Tutor - 交互式测试")
    print("=" * 60)
    print("""
请选择要测试的功能:

  [1] 创建样例 PDF
  [2] PDF 转图片 (Stage 0)
  [3] 视觉抽题 (Stage T) - Mock 模式
  [4] 求解 (Stage S) - Mock 模式
  [5] 诊断 (Stage D) - Mock 模式
  [6] 完整流程测试 - Mock 模式
  
  [7] 视觉抽题 (Stage T) - 真实 API
  [8] 求解 (Stage S) - 真实 API
  [9] 诊断 (Stage D) - 真实 API
  [10] 完整流程测试 - 真实 API
  
  [0] 退出
""")


def main():
    """主入口"""
    # 支持命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        use_mock = "--api" not in sys.argv
        
        if arg == "pdf":
            test_pdf_to_images()
        elif arg == "extract":
            test_vision_extract(image_paths=None, use_mock=False)
        elif arg == "solve":
            questions = load_questions_from_json("outputs/test_transcribed.json")
            if not questions:
                raise ValueError("Failed to load questions from JSON")
            test_solver(questions=questions, use_mock=False)
        elif arg == "diagnose":
            questions = load_questions_from_json("outputs/test_transcribed.json")
            if not questions:
                raise ValueError("Failed to load questions from JSON")
            results = load_solve_results("outputs/test_solve_results.json")
            if not results:
                raise ValueError("Failed to load solve results from JSON")
            test_diagnose(questions=questions, solve_results=results, user_answers=None, use_mock=False)
        elif arg == "full":
            test_full_pipeline(use_mock=use_mock)
        else:
            print(f"未知命令: {arg}")
            print("可用命令: pdf, extract, solve, diagnose, full")
            print("添加 --api 使用真实 API (需配置 OPENAI_API_KEY)")
        return
    
    # 交互模式
    while True:
        show_menu()
        try:
            choice = input("请输入选项 [0-10]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 再见!")
            break
        
        if choice == "0":
            print("\n👋 再见!")
            break
        elif choice == "2":
            test_pdf_to_images()
        elif choice == "3":
            test_vision_extract(use_mock=True)
        elif choice == "4":
            test_solver(use_mock=True)
        elif choice == "5":
            test_diagnose(use_mock=True)
        elif choice == "6":
            test_full_pipeline(use_mock=True)
        elif choice == "7":
            test_vision_extract(use_mock=False)
        elif choice == "8":
            test_solver(use_mock=False)
        elif choice == "9":
            test_diagnose(use_mock=False)
        elif choice == "10":
            test_full_pipeline(use_mock=False)
        else:
            print("❌ 无效选项")
        
        input("\n按 Enter 继续...")


if __name__ == "__main__":
    main()

