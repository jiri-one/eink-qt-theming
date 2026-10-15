// Offscreen widget gallery for previewing Qt styles without touching the screen.
// Build: g++ -std=c++17 -fPIC gallery.cpp -o gallery $(pkg-config --cflags --libs Qt6Widgets)
// Run:   QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME=qt5ct ./gallery out.png  (writes out.png and out-menu.png)
#include <QtWidgets>

static QTreeWidget *makePanel(int current)
{
    auto *tree = new QTreeWidget;
    tree->setHeaderLabels({"Name", "Ext", "Size", "Date"});
    tree->setRootIsDecorated(false);
    tree->setSelectionMode(QAbstractItemView::ExtendedSelection);
    const QStringList names{"..", "Documents", "Downloads", "Music", "Pictures", "Videos",
                            "invoice", "notes", "script", "backup", "book", "photo",
                            "export", "readme", "config", "data", "log", "map"};
    const QStringList exts{"", "", "", "", "", "", "pdf", "md", "sh", "tar.gz", "epub", "jpg",
                           "csv", "txt", "toml", "json", "log", "kml"};
    for (int i = 0; i < names.size(); ++i) {
        const bool dir = i < 6;
        auto *it = new QTreeWidgetItem(tree, {names[i], exts[i],
                                              dir ? "<DIR>" : QLocale().toString((i * 7919) % 99991),
                                              QString("2026-10-%1 08:%2").arg(1 + i % 14, 2, 10, QChar('0')).arg(i * 3 % 60, 2, 10, QChar('0'))});
        it->setIcon(0, QIcon::fromTheme(dir ? "folder" : "text-x-generic"));
    }
    tree->topLevelItem(7)->setSelected(true);
    tree->topLevelItem(8)->setSelected(true);
    tree->setCurrentItem(tree->topLevelItem(current), 0, QItemSelectionModel::NoUpdate);
    for (int c = 0; c < 4; ++c)
        tree->resizeColumnToContents(c);
    return tree;
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    const QString out = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QStringLiteral("gallery.png");

    const QPalette pal = QApplication::palette();
    QStringList roles;
    for (auto [name, role] : std::initializer_list<std::pair<const char *, QPalette::ColorRole>>{
             {"Window", QPalette::Window}, {"WindowText", QPalette::WindowText}, {"Base", QPalette::Base},
             {"AlternateBase", QPalette::AlternateBase}, {"Text", QPalette::Text}, {"Button", QPalette::Button},
             {"ButtonText", QPalette::ButtonText}, {"Light", QPalette::Light}, {"Midlight", QPalette::Midlight},
             {"Mid", QPalette::Mid}, {"Dark", QPalette::Dark}, {"Shadow", QPalette::Shadow},
             {"Highlight", QPalette::Highlight}, {"HighlightedText", QPalette::HighlightedText},
             {"Link", QPalette::Link}, {"ToolTipBase", QPalette::ToolTipBase}, {"PlaceholderText", QPalette::PlaceholderText}})
        roles << QString("%1=%2").arg(name, pal.color(QPalette::Active, role).name());
    fprintf(stderr, "fixed=%s\n", qPrintable(QFontInfo(QFontDatabase::systemFont(QFontDatabase::FixedFont)).family()));
    fprintf(stderr, "style=%s font=%s icons=%s\npalette: %s\ndisabled text=%s\n",
            qPrintable(QApplication::style()->name()), qPrintable(QApplication::font().toString()),
            qPrintable(QIcon::themeName()), qPrintable(roles.join(' ')),
            qPrintable(pal.color(QPalette::Disabled, QPalette::Text).name()));

    QMainWindow win;
    win.setWindowTitle("Gallery");
    auto *fileMenu = win.menuBar()->addMenu("&File");
    for (auto m : {"&Edit", "&View", "&Tools", "&Help"})
        win.menuBar()->addMenu(m);

    auto *tb = win.addToolBar("main");
    for (auto name : {"go-previous", "go-next", "go-up", "view-refresh", "edit-copy", "edit-cut",
                      "edit-delete", "folder-new", "edit-find", "document-properties"})
        tb->addAction(QIcon::fromTheme(name), name);

    auto *central = new QWidget;
    auto *v = new QVBoxLayout(central);

    auto *split = new QSplitter;
    for (int side = 0; side < 2; ++side) {
        auto *pane = new QWidget;
        auto *pv = new QVBoxLayout(pane);
        pv->setContentsMargins(0, 0, 0, 0);
        auto *tabs = new QTabBar;
        tabs->addTab(side ? "Videos" : "Downloads");
        tabs->addTab("home");
        pv->addWidget(tabs);
        pv->addWidget(new QLabel(side ? "/home/user/Videos" : "/home/user/Downloads"));
        auto *tree = makePanel(side ? 4 : 2);
        pv->addWidget(tree);
        pv->addWidget(new QLabel("2 of 18 files selected"));
        split->addWidget(pane);
        if (side == 0)
            tree->setFocus();
    }
    v->addWidget(split, 1);

    auto *controls = new QGroupBox("Controls");
    auto *g = new QGridLayout(controls);
    auto *cb1 = new QCheckBox("Checked");
    cb1->setChecked(true);
    g->addWidget(cb1, 0, 0);
    g->addWidget(new QCheckBox("Unchecked"), 0, 1);
    auto *rb1 = new QRadioButton("Option A");
    rb1->setChecked(true);
    g->addWidget(rb1, 0, 2);
    g->addWidget(new QRadioButton("Option B"), 0, 3);
    auto *combo = new QComboBox;
    combo->addItems({"By name", "By date"});
    g->addWidget(combo, 1, 0);
    auto *edit = new QLineEdit("~/Downloads/*.pdf");
    g->addWidget(edit, 1, 1);
    auto *spin = new QSpinBox;
    spin->setValue(42);
    g->addWidget(spin, 1, 2);
    auto *progress = new QProgressBar;
    progress->setValue(60);
    g->addWidget(progress, 1, 3);
    auto *slider = new QSlider(Qt::Horizontal);
    slider->setValue(30);
    g->addWidget(slider, 2, 0);
    auto *ok = new QPushButton("OK");
    ok->setDefault(true);
    g->addWidget(ok, 2, 1);
    auto *disabled = new QPushButton("Disabled");
    disabled->setEnabled(false);
    g->addWidget(disabled, 2, 2);
    auto *disabledEdit = new QLineEdit("disabled text");
    disabledEdit->setEnabled(false);
    g->addWidget(disabledEdit, 2, 3);
    v->addWidget(controls);

    auto *fkeys = new QHBoxLayout;
    for (auto label : {"F3 View", "F4 Edit", "F5 Copy", "F6 Move", "F7 Mkdir", "F8 Delete"})
        fkeys->addWidget(new QPushButton(label));
    v->addLayout(fkeys);

    win.setCentralWidget(central);
    win.statusBar()->showMessage("812 GB free");
    const QStringList size = qEnvironmentVariable("GALLERY_SIZE", "1500x1100").split('x');
    win.resize(size.value(0).toInt(), size.value(1).toInt());
    win.show();
    win.activateWindow();

    QMenu menu;
    menu.addAction(QIcon::fromTheme("edit-copy"), "Copy", QKeySequence("F5"));
    menu.addAction(QIcon::fromTheme("edit-delete"), "Delete", QKeySequence("F8"));
    menu.addSeparator();
    auto *check = menu.addAction("Hidden files");
    check->setCheckable(true);
    check->setChecked(true);
    menu.addMenu("Sort by");
    auto *dis = menu.addAction("Disabled item");
    dis->setEnabled(false);
    menu.setActiveAction(menu.actions().at(1));

    QTimer::singleShot(qEnvironmentVariableIntegerValue("GALLERY_DELAY").value_or(300), [&] {
#if QT_VERSION >= QT_VERSION_CHECK(6, 10, 0)
        fprintf(stderr, "contrast at grab=%d\n", int(QGuiApplication::styleHints()->accessibility()->contrastPreference()));
#endif
        if (!win.grab().save(out)) {
            fprintf(stderr, "Could not write %s\n", qPrintable(out));
            app.exit(1);
            return;
        }
        menu.popup(QPoint(0, 0));
        menu.setActiveAction(menu.actions().at(1));
        QTimer::singleShot(300, [&] {
            QString menuOut = out;
            menuOut.replace(".png", "-menu.png");
            app.exit(menu.grab().save(menuOut) ? 0 : 1);
        });
    });
    Q_UNUSED(fileMenu);
    return app.exec();
}
