#pragma once

#include "common/model.h"
#include "selfdrive/ui/ui.h"
#include "selfdrive/ui/qt/util.h"
#include "selfdrive/ui/qt/widgets/controls.h"
#include "selfdrive/ui/qt/widgets/scrollview.h"


//////////////////////////////////////////////////////////////
class ContinuousLaneChangeCnt : public SPOptionControl {
  Q_OBJECT

public:
  ContinuousLaneChangeCnt();
  void refresh();
private:
  Params params;
};

class ContinuousLaneChangeInterval : public SPOptionControl {
  Q_OBJECT

public:
  ContinuousLaneChangeInterval();
  void refresh();
private:
  Params params;
};

class LaneStabTime : public SPOptionControl {
  Q_OBJECT

public:
  LaneStabTime();
  void refresh();
private:
  Params params;
};

class BsdDelayTime : public SPOptionControl {
  Q_OBJECT

public:
  BsdDelayTime();
  void refresh();
private:
  Params params;
};

class SideBsdDelayTime : public SPOptionControl {
  Q_OBJECT

public:
  SideBsdDelayTime();
  void refresh();
private:
  Params params;
};

class SideRelDistTime : public SPOptionControl {
  Q_OBJECT

public:
  SideRelDistTime();
  void refresh();
private:
  Params params;
};

class SidevRelDistTime : public SPOptionControl {
  Q_OBJECT

public:
  SidevRelDistTime();
  void refresh();
private:
  Params params;
};

class SideRadarMinDist : public SPOptionControl {
  Q_OBJECT

public:
  SideRadarMinDist();
  void refresh();
private:
  Params params;
};

//////////////////////////////////////////////////////////////
class AutoCurveSpeedFactorH : public SPOptionControl {
  Q_OBJECT

public:
  AutoCurveSpeedFactorH();
  void refresh();
private:
  Params params;
};

class AutoCurveSpeedAggressivenessH : public SPOptionControl {
  Q_OBJECT

public:
  AutoCurveSpeedAggressivenessH();
  void refresh();
private:
  Params params;
};

class AutoCurveSpeedFactor : public SPOptionControl {
  Q_OBJECT

public:
  AutoCurveSpeedFactor();
  void refresh();
private:
  Params params;
};

class AutoCurveSpeedAggressiveness : public SPOptionControl {
  Q_OBJECT

public:
  AutoCurveSpeedAggressiveness();
  void refresh();
private:
  Params params;
};

//////////////////////////////////////////////////////////////
class AutoForkDistOffsetH : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkDistOffsetH();
  void refresh();
private:
  Params params;
};

class AutoDoForkDecalDistH : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkDecalDistH();
  void refresh();
private:
  Params params;
};

class AutoForkDecalRateH : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkDecalRateH();
  void refresh();
private:
  Params params;
};

class AutoForkSpeedMinH : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkSpeedMinH();
  void refresh();
private:
  Params params;
};

class AutoDoForkBlinkerDistH : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkBlinkerDistH();
  void refresh();
private:
  Params params;
};

class AutoDoForkNavDistH : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkNavDistH();
  void refresh();
private:
  Params params;
};

class AutoKeepForkSpeedH : public SPOptionControl {
  Q_OBJECT

public:
  AutoKeepForkSpeedH();
  void refresh();
private:
  Params params;
};

class AutoEnTurnNewLaneTimeH : public SPOptionControl {
  Q_OBJECT

public:
  AutoEnTurnNewLaneTimeH();
  void refresh();
private:
  Params params;
};

class AutoUpHighwayRoadLimit40KMH : public SPOptionControl {
  Q_OBJECT

public:
  AutoUpHighwayRoadLimit40KMH();
  void refresh();
private:
  Params params;
};

//////////////////////////////////////////////////////////////
class AutoForkDistOffset : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkDistOffset();
  void refresh();
private:
  Params params;
};

class AutoDoForkDecalDist : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkDecalDist();
  void refresh();
private:
  Params params;
};


class AutoForkDecalRate : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkDecalRate();
  void refresh();
private:
  Params params;
};

class AutoForkSpeedMin : public SPOptionControl {
  Q_OBJECT

public:
  AutoForkSpeedMin();
  void refresh();
private:
  Params params;
};

class AutoDoForkBlinkerDist : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkBlinkerDist();
  void refresh();
private:
  Params params;
};

class AutoDoForkNavDist : public SPOptionControl {
  Q_OBJECT

public:
  AutoDoForkNavDist();
  void refresh();
private:
  Params params;
};

class AutoKeepForkSpeed : public SPOptionControl {
  Q_OBJECT

public:
  AutoKeepForkSpeed();
  void refresh();
private:
  Params params;
};

class AutoEnTurnNewLaneTime : public SPOptionControl {
  Q_OBJECT

public:
  AutoEnTurnNewLaneTime();
  void refresh();
private:
  Params params;
};

class AutoUpRoadLimit40KMH : public SPOptionControl {
  Q_OBJECT

public:
  AutoUpRoadLimit40KMH();
  void refresh();
private:
  Params params;
};

class CpSpdAndRoadLimit : public SPOptionControl {
  Q_OBJECT

public:
  CpSpdAndRoadLimit();
  void refresh();
private:
  Params params;
};

class RoadType : public SPOptionControl {
  Q_OBJECT

public:
  RoadType();
  void refresh();
private:
  Params params;
};

/***********************************************************/
class NavPanel : public QFrame {
  Q_OBJECT

public:
  explicit NavPanel(QWidget *parent = nullptr);
  void showEvent(QShowEvent *event) override;
  void hideEvent(QHideEvent* event) override;

public slots:
  void updateToggles();
  void updateToggles(const QString &param_name, const QString &param_value);

private:
  QStackedLayout* main_layout = nullptr;
  QWidget* navScreen = nullptr;
  Params params;
  std::map<std::string, ParamControl*> toggles;
  ParamWatcher *param_watcher;
  ScrollView *scrollView = nullptr;

  ContinuousLaneChangeCnt       * continuouslanechangecnt        ;
  ContinuousLaneChangeInterval  * continuouslanechangeinterval   ;
  LaneStabTime                  * lanestabtime                   ;
  BsdDelayTime                  * bsddelaytime                   ;
  SideBsdDelayTime              * sidebsddelaytime               ;
  SideRelDistTime               * sidereldisttime                ;
  SidevRelDistTime              * sidevreldisttime               ;
  SideRadarMinDist              * sideradarmindist               ;

  AutoCurveSpeedFactorH         * autocurvespeedfactorh          ;
  AutoCurveSpeedAggressivenessH * autocurvespeedaggressivenessh  ;
  AutoCurveSpeedFactor          * autocurvespeedfactor           ;
  AutoCurveSpeedAggressiveness  * autocurvespeedaggressiveness   ;

  AutoForkDistOffsetH           * autoforkdistoffseth            ;
  AutoDoForkDecalDistH          * autodoforkdecaldisth           ;
  AutoForkDecalRateH            * autoforkdecalrateh             ;
  AutoForkSpeedMinH             * autoforkspeedminh              ;
  AutoDoForkBlinkerDistH        * autodoforkblinkerdisth         ;
  AutoDoForkNavDistH            * autodoforknavdisth             ;
  AutoKeepForkSpeedH            * autokeepforkspeedh             ;
  AutoEnTurnNewLaneTimeH        * autoenturnnewlanetimeh         ;
  AutoUpHighwayRoadLimit40KMH   * autouphighwayroadlimit40kmh    ;

  AutoForkDistOffset            * autoforkdistoffset             ;
  AutoDoForkDecalDist           * autodoforkdecaldist            ;
  AutoForkDecalRate             * autoforkdecalrate              ;
  AutoForkSpeedMin              * autoforkspeedmin               ;
  AutoDoForkBlinkerDist         * autodoforkblinkerdist          ;
  AutoDoForkNavDist             * autodoforknavdist              ;
  AutoKeepForkSpeed             * autokeepforkspeed              ;
  AutoEnTurnNewLaneTime         * autoenturnnewlanetime          ;
  AutoUpRoadLimit40KMH          * autouproadlimit40kmh           ;

  CpSpdAndRoadLimit             * cpspdandroadlimit              ;
  RoadType                      * roadtype                       ;
};

