#pragma once

#include "common/model.h"
#include "selfdrive/ui/ui.h"
#include "selfdrive/ui/qt/util.h"
#include "selfdrive/ui/qt/widgets/controls.h"
#include "selfdrive/ui/qt/widgets/scrollview.h"

class StartTurnLatA : public SPOptionControl {
  Q_OBJECT

public:
  StartTurnLatA();
  void refresh();
private:
  Params params;
};

class TargetTurnLatA : public SPOptionControl {
  Q_OBJECT

public:
  TargetTurnLatA();
  void refresh();
private:
  Params params;
};

class TurnSteepNess : public SPOptionControl {
  Q_OBJECT

public:
  TurnSteepNess();
  void refresh();
private:
  Params params;
};

class TurnLatAccel : public SPOptionControl {
  Q_OBJECT

public:
  TurnLatAccel();
  void refresh();
private:
  Params params;
};

class EndTurnLatAccel : public SPOptionControl {
  Q_OBJECT

public:
  EndTurnLatAccel();
  void refresh();
private:
  Params params;
};

class TurnMaxFactor : public SPOptionControl {
  Q_OBJECT

public:
  TurnMaxFactor();
  void refresh();
private:
  Params params;
};

class SteerTurnThr : public SPOptionControl {
  Q_OBJECT

public:
  SteerTurnThr();
  void refresh();
private:
  Params params;
};

class SteerMaxFactor : public SPOptionControl {
  Q_OBJECT

public:
  SteerMaxFactor();
  void refresh();
private:
  Params params;
};

class StopDistance : public SPOptionControl {
  Q_OBJECT

public:
  StopDistance();
  void refresh();
private:
  Params params;
};

class CruiseOnDist : public SPOptionControl {
  Q_OBJECT

public:
  CruiseOnDist();
  void refresh();
private:
  Params params;
};

class ComfortBrake : public SPOptionControl {
  Q_OBJECT

public:
  ComfortBrake();
  void refresh();
private:
  Params params;
};

class StartAccel : public SPOptionControl {
  Q_OBJECT

public:
  StartAccel();
  void refresh();
private:
  Params params;
};

class StopAccel : public SPOptionControl {
  Q_OBJECT

public:
  StopAccel();
  void refresh();
private:
  Params params;
};

class MaxStopAccel : public SPOptionControl {
  Q_OBJECT

public:
  MaxStopAccel();
  void refresh();
private:
  Params params;
};

class vEgoStopping : public SPOptionControl {
  Q_OBJECT

public:
  vEgoStopping();
  void refresh();
private:
  Params params;
};

class ExperimentalModeSpeed : public SPOptionControl {
  Q_OBJECT

public:
  ExperimentalModeSpeed();
  void refresh();
private:
  Params params;
};

class ExperimentalModeAndSpeed : public SPOptionControl {
  Q_OBJECT

public:
  ExperimentalModeAndSpeed();
  void refresh();
private:
  Params params;
};

class ExperimentalModeAngle : public SPOptionControl {
  Q_OBJECT

public:
  ExperimentalModeAngle();
  void refresh();
private:
  Params params;
};

class JEgoCost : public SPOptionControl {
  Q_OBJECT

public:
  JEgoCost();
  void refresh();
private:
  Params params;
};

class AChangeCostStart : public SPOptionControl {
  Q_OBJECT

public:
  AChangeCostStart();
  void refresh();
private:
  Params params;
};

class AChangeCost : public SPOptionControl {
  Q_OBJECT

public:
  AChangeCost();
  void refresh();
private:
  Params params;
};

class ShortPressInc : public SPOptionControl {
  Q_OBJECT

public:
  ShortPressInc();
  void refresh();
private:
  Params params;
};

class LongPressInc : public SPOptionControl {
  Q_OBJECT

public:
  LongPressInc();
  void refresh();
private:
  Params params;
};

class UserFuncPanel : public QFrame {
  Q_OBJECT

public:
  explicit UserFuncPanel(QWidget *parent = nullptr);
  void showEvent(QShowEvent *event) override;
  void hideEvent(QHideEvent* event) override;

public slots:
  void updateToggles();
  void updateToggles(const QString &param_name, const QString &param_value);

private:
  QStackedLayout* main_layout = nullptr;
  QWidget* userScreen = nullptr;
  Params params;
  std::map<std::string, ParamControl*> toggles;
  ParamWatcher *param_watcher;
  ScrollView *scrollView = nullptr;

  StopDistance *stop_distance;
  ComfortBrake *comfort_break;
  StartAccel *start_accel;
  StopAccel *stop_accel;
  MaxStopAccel *max_stop_accel;
  vEgoStopping *vego_stopping;

  ExperimentalModeAngle *experimental_mode_angle;
  ExperimentalModeAndSpeed *experimental_mode_and_speed;
  ExperimentalModeSpeed *experimental_mode_speed;

  TargetTurnLatA *target_turn_lat_a;
  StartTurnLatA *start_turn_lat_a;

  TurnSteepNess *turn_steep_ness;
  TurnLatAccel *turn_lat_acc;
  EndTurnLatAccel *end_turn_lat_acc;
  TurnMaxFactor *turn_max_factor;

  SteerTurnThr *steer_turn_thr;
  SteerMaxFactor *steer_max_factor;

  JEgoCost *j_ego_cost;
  AChangeCostStart *a_change_cost_start;
  AChangeCost *a_change_cost;

  LabelControl *label_start_turn_lat_a;
  LabelControl *label_target_turn_lat_a;

  LabelControl *label_turn_steep_ness;
  LabelControl *label_turn_lat_accel;
  LabelControl *label_end_turn_lat_accel;
  LabelControl *label_turn_max_factor;

  LabelControl *label_steer_turn_thr;
  LabelControl *label_steer_max_factor;

  LabelControl *label_experimental_angle_and_speed;
  LabelControl *label_experimental_speed;
  ParamControl *toggle_dm;

  LabelControl *label_stop_distance;
  LabelControl *label_comfort_break;
  LabelControl *label_max_stop_accel;
  LabelControl *label_start_accel;
  LabelControl *label_stop_accel;
  LabelControl *label_vego_stopping;
  LabelControl *label_j_ego_cost;
  LabelControl *label_a_change_cost_start;
  LabelControl *label_a_change_cost;

  ShortPressInc *short_press_inc;
  LongPressInc *long_press_inc;

  LabelControl *label_short_press_inc;
  LabelControl *label_long_press_inc;
};
