#pragma once

#include <QPainter>
#include <QString>
#include "selfdrive/ui/ui.h"

class TurnInfoDrawer {
public:
  TurnInfoDrawer();

  void update(const SubMaster &sm);
  void draw(QPainter &p, const UIState *s);

private:
  int icon_size = 160;
  int xTurnInfo = -1;
  int xDistToTurn = 0;
  int active_carrot = 0;
  int nGoPosDist = 0;
  int nGoPosTime = 0;

  QString szSdiDescr;
  QString szPosRoadName;
  QString szTBTMainText;
  QString atc_type;

  QPixmap ic_turn_l, ic_turn_r, ic_turn_u, ic_lane_change_l, ic_lane_change_r;
};
