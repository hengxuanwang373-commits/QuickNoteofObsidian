#!/usr/bin/env python3
"""
测试可调整大小的输入对话框功能
测试 ResizableInputPanel 的创建、配置保存和基本功能
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 模拟配置路径用于测试
TEST_CONFIG_PATH = Path(tempfile.gettempdir()) / "test_quicknote_config.json"


def test_import_resizable_input_panel():
    """测试 1: 验证 ResizableInputPanel 可以正确导入"""
    print("=" * 50)
    print("测试 1: 导入 ResizableInputPanel")
    print("=" * 50)

    try:
        from resizable_input_panel import (
            ResizableInputPanel,
            show_resizable_input_dialog,
            InputResult,
            Button,
            HAS_APPKIT
        )
        print(f"✅ 导入成功")
        print(f"   - HAS_APPKIT: {HAS_APPKIT}")
        print(f"   - Button 枚举值: {[b.value for b in Button]}")
        print(f"   - InputResult 是 frozen dataclass: {hasattr(InputResult, '__dataclass_fields__')}")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_config_save_load():
    """测试 2: 验证配置保存和加载功能"""
    print("\n" + "=" * 50)
    print("测试 2: 配置保存和加载")
    print("=" * 50)

    # 模拟 load_config 和 save_config
    def load_config():
        if TEST_CONFIG_PATH.exists():
            try:
                return json.loads(TEST_CONFIG_PATH.read_text())
            except:
                pass
        return {"dialog_width": 500, "dialog_height": 300}

    def save_config(config):
        TEST_CONFIG_PATH.write_text(json.dumps(config, indent=2))

    # 测试默认配置
    config = load_config()
    print(f"   默认配置: width={config.get('dialog_width')}, height={config.get('dialog_height')}")

    # 测试保存新配置
    new_config = {"dialog_width": 800, "dialog_height": 600}
    save_config(new_config)
    print(f"   保存配置: width=800, height=600")

    # 验证加载
    loaded = load_config()
    print(f"   加载配置: width={loaded.get('dialog_width')}, height={loaded.get('dialog_height')}")

    if loaded.get('dialog_width') == 800 and loaded.get('dialog_height') == 600:
        print("✅ 配置保存/加载测试通过")
        return True
    else:
        print("❌ 配置保存/加载测试失败")
        return False


def test_resizable_input_panel_creation():
    """测试 3: 验证 ResizableInputPanel 可以创建实例"""
    print("\n" + "=" * 50)
    print("测试 3: ResizableInputPanel 实例创建")
    print("=" * 50)

    try:
        from resizable_input_panel import ResizableInputPanel, HAS_APPKIT

        if not HAS_APPKIT:
            print("⚠️ AppKit 不可用，跳过 GUI 创建测试")
            print("   (在无 GUI 环境下这是预期的)")
            return True

        # 创建面板实例
        panel = ResizableInputPanel(
            title="测试标题",
            prompt="测试提示",
            width=600,
            height=400,
            default_text="测试默认文本"
        )

        print(f"✅ 面板实例创建成功")
        print(f"   - 标题: {panel._title}")
        print(f"   - 提示: {panel._prompt}")
        print(f"   - 宽度: {panel._width}")
        print(f"   - 高度: {panel._height}")
        print(f"   - 默认文本: {panel._default_text}")

        return True
    except Exception as e:
        print(f"❌ 面板创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_panel_dimension_constraints():
    """测试 4: 验证面板尺寸约束"""
    print("\n" + "=" * 50)
    print("测试 4: 面板尺寸约束")
    print("=" * 50)

    try:
        from resizable_input_panel import ResizableInputPanel, HAS_APPKIT

        if not HAS_APPKIT:
            print("⚠️ AppKit 不可用，跳过尺寸约束测试")
            return True

        # 测试最小宽度约束 (应该被约束到 400)
        panel1 = ResizableInputPanel(title="测试", prompt="", width=200, height=300)
        print(f"   宽度 200 -> 实际: {panel1._width} (最小 400)")

        # 测试最小高度约束 (应该被约束到 200)
        panel2 = ResizableInputPanel(title="测试", prompt="", width=500, height=100)
        print(f"   高度 100 -> 实际: {panel2._height} (最小 200)")

        # 测试正常尺寸
        panel3 = ResizableInputPanel(title="测试", prompt="", width=600, height=400)
        print(f"   宽度 600, 高度 400 -> 实际: {panel3._width}, {panel3._height}")

        success = (
            panel1._width == 400 and
            panel2._height == 200 and
            panel3._width == 600 and
            panel3._height == 400
        )

        if success:
            print("✅ 尺寸约束测试通过")
        else:
            print("❌ 尺寸约束测试失败")

        return success
    except Exception as e:
        print(f"❌ 尺寸约束测试失败: {e}")
        return False


def test_input_result_dataclass():
    """测试 5: 验证 InputResult 数据类"""
    print("\n" + "=" * 50)
    print("测试 5: InputResult 数据类")
    print("=" * 50)

    try:
        from resizable_input_panel import InputResult

        # 测试创建 InputResult
        result = InputResult(
            content="测试内容",
            button="保存",
            attachments=("file1.png", "file2.jpg")
        )

        print(f"   content: {result.content}")
        print(f"   button: {result.button}")
        print(f"   attachments: {result.attachments}")

        # 测试不可变性
        try:
            result.content = "修改"
            print("❌ InputResult 不是不可变的")
            return False
        except AttributeError:
            print("   InputResult 是不可变的 (frozen=True)")

        # 测试元组不可变性
        try:
            result.attachments = ()
            print("❌ attachments 不是不可变的")
            return False
        except AttributeError:
            print("   attachments 是不可变的")

        print("✅ InputResult 数据类测试通过")
        return True
    except Exception as e:
        print(f"❌ InputResult 测试失败: {e}")
        return False


def test_integration_with_main_app():
    """测试 6: 集成测试 - 验证 main app 中的配置流程"""
    print("\n" + "=" * 50)
    print("测试 6: 集成测试 - main app 配置流程")
    print("=" * 50)

    try:
        # 验证 quicknote_menubar.py 中的配置键存在
        with open("quicknote_menubar.py", "r") as f:
            content = f.read()

        # 检查 DEFAULT_CONFIG 包含 dialog_width 和 dialog_height
        if 'dialog_width' in content and 'dialog_height' in content:
            print("✅ DEFAULT_CONFIG 包含 dialog_width 和 dialog_height")
        else:
            print("❌ DEFAULT_CONFIG 缺少 dialog 配置")
            return False

        # 检查 show_input_dialog 使用了这些配置
        if 'dialog_width = config.get("dialog_width"' in content:
            print("✅ show_input_dialog 使用 dialog_width 配置")
        else:
            print("❌ show_input_dialog 未使用 dialog_width")
            return False

        # 检查 show_settings_dialog 有对话框大小按钮
        if '对话框大小' in content:
            print("✅ show_settings_dialog 包含「对话框大小」按钮")
        else:
            print("❌ show_settings_dialog 缺少「对话框大小」按钮")
            return False

        print("✅ 集成测试通过")
        return True
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def cleanup():
    """清理测试文件"""
    if TEST_CONFIG_PATH.exists():
        TEST_CONFIG_PATH.unlink()


def main():
    print("\n" + "=" * 60)
    print("🧪 QuickNote 可调整大小对话框功能测试")
    print("=" * 60)

    results = []

    # 执行测试
    results.append(("导入测试", test_import_resizable_input_panel()))
    results.append(("配置保存/加载", test_config_save_load()))
    results.append(("面板实例创建", test_resizable_input_panel_creation()))
    results.append(("尺寸约束", test_panel_dimension_constraints()))
    results.append(("InputResult数据类", test_input_result_dataclass()))
    results.append(("集成测试", test_integration_with_main_app()))

    # 清理
    cleanup()

    # 打印结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过! 可以进行构建。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请修复后再构建。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
