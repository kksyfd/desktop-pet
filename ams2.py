import ams1 as a
import sys
def main():
    app = a.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # 添加这一行
    window = a.MainWindow()
    window.show()
    print("=" * 60)
    print("🖱️  鼠标跟踪: 眼睛跟随鼠标")
    print("✋ 右手手势: 1,2,3,4, q,w,e,r, a,s,d,f, space, shift, tab")
    print("💬 头顶对话框: 按任意字母/数字/功能键显示")
    print("🔍 右键拖动: 放大/缩小")
    print("=" * 60)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()