// Renders a menu the way a compositor shows it (translucent frame, shadow, real scale) without opening a window:
// the offscreen platform has no compositor, so Kvantum would draw a different, opaque menu frame there.
// Build: g++ -std=c++17 -fPIC menugrab.cpp -o menugrab $(pkg-config --cflags --libs Qt6Widgets)
// Run:   QT_QPA_PLATFORM=wayland ./menugrab menu.png   (inside a Wayland session)
#include <QtWidgets>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    if (argc < 2) {
        fprintf(stderr, "Usage: %s out.png\n", argv[0]);
        return 2;
    }
    QMenu menu;
    menu.addAction(QIcon::fromTheme("edit-copy"), "Copy", QKeySequence("F5"));
    menu.addAction(QIcon::fromTheme("edit-delete"), "Delete", QKeySequence("F8"));
    menu.addSeparator();
    auto *check = menu.addAction("Hidden files");
    check->setCheckable(true);
    check->setChecked(true);
    menu.addMenu("Sort by")->addAction("Name");
    menu.addAction("Disabled item")->setEnabled(false);
    menu.ensurePolished();
    menu.adjustSize();
    menu.setActiveAction(menu.actions().at(0));
    QPixmap pm = menu.grab();
    QImage out(pm.size(), QImage::Format_ARGB32);
    out.setDevicePixelRatio(pm.devicePixelRatio());
    out.fill(Qt::white);
    QPainter p(&out);
    p.drawPixmap(0, 0, pm);
    p.end();
    fprintf(stderr, "platform=%s style=%s size=%dx%d translucent=%d hmargin=%d vmargin=%d\n",
            qPrintable(QGuiApplication::platformName()), qPrintable(app.style()->name()), pm.width(), pm.height(),
            menu.testAttribute(Qt::WA_TranslucentBackground),
            app.style()->pixelMetric(QStyle::PM_MenuHMargin, nullptr, &menu),
            app.style()->pixelMetric(QStyle::PM_MenuVMargin, nullptr, &menu));
    if (!out.save(QString::fromLocal8Bit(argv[1]))) {
        fprintf(stderr, "Could not write %s\n", argv[1]);
        return 1;
    }
    return 0;
}
