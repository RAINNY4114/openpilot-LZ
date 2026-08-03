#include "selfdrive/ui/qt/widgets/turn_info_drawer.h"
#include <ctime>

TurnInfoDrawer::TurnInfoDrawer() {
  // 加载图标资源
  ic_turn_l = QPixmap("/data/openpilot/selfdrive/assets/images/turn_l.png");
  ic_turn_r = QPixmap("/data/openpilot/selfdrive/assets/images/turn_r.png");
  ic_turn_u = QPixmap("/data/openpilot/selfdrive/assets/images/turn_u.png");
  ic_lane_change_l = QPixmap("/data/openpilot/selfdrive/assets/images/lane_change_l.png");
  ic_lane_change_r = QPixmap("/data/openpilot/selfdrive/assets/images/lane_change_r.png");
}

void TurnInfoDrawer::update(const SubMaster &sm) {
  if (!sm.alive("carrotMan")) {
    active_carrot = 0;
    nGoPosDist = 0;
    nGoPosTime = 0;
    return;
  }

  const auto carrot_man = sm["carrotMan"].getCarrotMan();
  active_carrot = carrot_man.getActiveCarrot();

  if (active_carrot > 1 || carrot_man.getNGoPosDist() > 0) {
    xTurnInfo = carrot_man.getXTurnInfo();
    xDistToTurn = carrot_man.getXDistToTurn();
    nGoPosDist = carrot_man.getNGoPosDist();
    nGoPosTime = carrot_man.getNGoPosTime();
    szSdiDescr = QString::fromStdString(carrot_man.getSzSdiDescr());
    szPosRoadName = QString::fromStdString(carrot_man.getSzPosRoadName());
    szTBTMainText = QString::fromStdString(carrot_man.getSzTBTMainText());
    atc_type = QString::fromStdString(carrot_man.getAtcType());
  }
}

void TurnInfoDrawer::draw(QPainter &p, const UIState *s) {
  if (s->fb_w < 1200) return;
  if (nGoPosDist <= 0 || nGoPosTime <= 0) return;

  int tbt_x = s->fb_w - 800;
  int tbt_y = s->fb_h - 250;

  // ================= 大背景 =================
  p.setRenderHint(QPainter::Antialiasing);
  p.setPen(QPen(Qt::white, 2));
  p.setBrush(QColor(0, 0, 0, 120));
  p.drawRoundedRect(QRect(tbt_x, tbt_y - 60, 790, 300), 30, 30);

  // ================= 字体设置：半粗体 =================
  QFont font("KaiGenGothicKR-Bold");
  font.setPointSize(30);
  font.setWeight(QFont::DemiBold);
  p.setFont(font);
  p.setPen(Qt::white);

  // 主文本
  if (!szTBTMainText.isEmpty()) {
    p.drawText(tbt_x + 20, tbt_y - 5, szTBTMainText);
  }

  // ================= 转弯图标 + 背景 + xDistToTurn =================
  if (xTurnInfo > 0) {
      // ===================== 基础坐标 =====================
      int bx = tbt_x + 110;
      // 图标中心的 X 坐标（在 TBT 框左上角往右偏移 100px）

      int by = tbt_y + 85;
      // 图标中心的 Y 坐标（在 TBT 框上边缘往下偏移 85px）

      // ===================== 图标选择 =====================
      QPixmap *icon = nullptr;
      switch (xTurnInfo) {
        case 1: icon = &ic_turn_l; break;        // 左转
        case 2: icon = &ic_turn_r; break;        // 右转
        case 3: icon = &ic_lane_change_l; break; // 左变道
        case 4: icon = &ic_lane_change_r; break; // 右变道
        case 7: icon = &ic_turn_u; break;        // 掉头
      }

      // ===================== 背景矩形 =====================
      int bg_top = tbt_y + 14;
      // 背景矩形的顶部 Y 坐标（主文本下方约 1mm）

      int dist_text_y = by + 120;
      // 距离文字基线的 Y 坐标（文字绘制位置的参考点）

      int bg_bottom = dist_text_y + 20;
      // 背景矩形的底部 Y 坐标（比文字再往下延伸 1.5mm）

      int bg_h = bg_bottom - bg_top;
      // 背景矩形的高度 = bottom - top

      int bg_w = 180;
      // 背景矩形的固定宽度（左右各比图标缩小 2mm）

      int bg_x = bx - bg_w / 2;
      // 背景矩形的左上角 X 坐标 = 图标中心 - 半宽

      int bg_y = bg_top;
      // 背景矩形的左上角 Y 坐标 = top

      if (icon && !icon->isNull()) {
        // 绘制绿色渐变背景
        QLinearGradient gradient(bg_x, bg_y, bg_x, bg_y + bg_h);
        gradient.setColorAt(0, QColor(0, 255, 0, 220)); // 上方亮绿
        gradient.setColorAt(1, QColor(0, 128, 0, 180)); // 下方深绿

        p.setBrush(gradient);
        p.setPen(Qt::NoPen);
        p.setRenderHint(QPainter::Antialiasing);
        p.drawRoundedRect(QRect(bg_x, bg_y, bg_w, bg_h), 20, 20);

        // ===================== 图标 =====================
        QRect iconRect(
            bx - icon_size / 2,                  // 图标左上角 X
            bg_y + (bg_h - icon_size - 60) / 2,  // 图标左上角 Y（在背景中垂直居中，往上留 30px）
            icon_size,                           // 图标宽度
            icon_size                            // 图标高度
        );
        p.drawPixmap(iconRect, *icon);
      }

      // ===================== 距离文字 =====================
      QString dist_str;
      if (xDistToTurn < 1000)
        dist_str = QString("%1 m").arg(xDistToTurn);
      else
        dist_str = QString::asprintf("%.1f km", xDistToTurn / 1000.0);

      p.setPen(Qt::white);

      // 计算文字宽度
      QFontMetrics fm(p.font());
      int text_w = fm.horizontalAdvance(dist_str);

      int bg_center_x = bg_x + bg_w / 2;
      // 背景矩形的中心 X 坐标

      int text_y = by + 120;
      // 文字基线的 Y 坐标（固定在图标下方 120px）

      // 居中绘制距离文字，使其和背景水平居中对齐
      p.drawText(bg_center_x - text_w / 2, text_y, dist_str);
  }

  // ================= 道路名称 / SDI =================
  if (!szSdiDescr.isEmpty()) {
    QFontMetrics fm(p.font());

    int text_x = tbt_x + 220;
    // 文字绘制的起始 X 坐标（相对 TBT 框左上角右移 200px）

    int text_y = tbt_y + 200;
    // 文字基线 Y 坐标（相对 TBT 框左上角下移 200px）

    int padding_x = 20;
    // 背景左右内边距

    int padding_y = 8;
    // 背景上下内边距

    int text_w = fm.horizontalAdvance(szSdiDescr);
    // 文本实际宽度（像素）

    int text_h = fm.ascent() + fm.descent();
    // 文本实际高度（像素）

    QRect bgRect(
        text_x,                        // 背景左上角 X（与文字左边对齐）
        text_y - fm.ascent() - padding_y, // 背景左上角 Y（文字基线往上移 ascent，再多留 padding）
        text_w + padding_x * 2,        // 背景宽度（文字宽度 + 左右 padding）
        text_h + padding_y * 2         // 背景高度（文字高度 + 上下 padding）
    );

    // 背景：绿色半透明矩形
    p.setBrush(QColor(0, 180, 0, 200));
    p.setPen(Qt::NoPen);
    p.drawRoundedRect(bgRect, 10, 10);

    // 绘制文字
    p.setPen(Qt::white);
    // 左对齐绘制：X = text_x + padding_x，Y = 基线 text_y
    p.drawText(text_x + padding_x, text_y, szSdiDescr);

  } else if (!szPosRoadName.isEmpty()) {
    p.setPen(Qt::white);
    // 道路名文字直接画在 TBT 框左上角右移 200px，下移 200px
    p.drawText(tbt_x + 220, tbt_y + 200, szPosRoadName);
  }

  // ================= 到达时间和剩余距离 =================
  if (nGoPosDist > 0 && nGoPosTime > 0) {
    time_t now = time(NULL);
    struct tm *local = localtime(&now);
    int remaining_minutes = nGoPosTime / 60;
    local->tm_min += remaining_minutes;
    mktime(local);

    QString eta = QString::asprintf("到达: %.1f分(%02d:%02d)",
                                    (float)nGoPosTime / 60.,
                                    local->tm_hour, local->tm_min);

    p.setPen(Qt::white);
    // 到达时间文字：TBT 框左上角右移 220px，下移 80px
    p.drawText(tbt_x + 220, tbt_y + 80, eta);

    QString dist = QString::asprintf("%.1f km", nGoPosDist / 1000.0);
    // 剩余距离文字：TBT 框左上角右移 310px，下移 130px
    p.drawText(tbt_x + 310, tbt_y + 130, dist);
  }
}
