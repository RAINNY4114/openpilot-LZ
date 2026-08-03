#include "selfdrive/ui/qt/offroad/sunnypilot/nav_settings.h"




void NavPanel::showEvent(QShowEvent *event) {
  updateToggles();
}
void NavPanel::hideEvent(QHideEvent *event) {
  main_layout->setCurrentWidget(navScreen);
}
void NavPanel::updateToggles(const QString &param_name, const QString &param_value) {
  if (!isVisible()) return;
}
void NavPanel::updateToggles() {
  if (!isVisible()) {
    return;
  }
}

NavPanel::NavPanel(QWidget *parent) : QFrame(parent) {
  main_layout = new QStackedLayout(this);

  ListWidget *list = new ListWidget(this, false);

  list->addItem(horizontal_line());
  list->addItem(new LabelControl(tr("RoadType description")));
  list->addItem(horizontal_line());
  //============================================================

  auto samespicamfilter = new ParamControl(
    "SameSpiCamFilter",
    tr("SameSpiCamFilter"),
    tr("SameSpiCamFilter"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(samespicamfilter);
  toggles["SameSpiCamFilter"] = samespicamfilter;

  auto autoturninnotroadedge = new ParamControl(
    "AutoTurnInNotRoadEdge",
    tr("AutoTurnInNotRoadEdge"),
    tr("AutoTurnInNotRoadEdge"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(autoturninnotroadedge);
  toggles["AutoTurnInNotRoadEdge"] = autoturninnotroadedge;

  auto autoturnleft = new ParamControl(
    "AutoTurnLeft",
    tr("AutoTurnLeft"),
    tr("AutoTurnLeft"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(autoturnleft);
  toggles["AutoTurnLeft"] = autoturnleft;

  auto continuouslanechange = new ParamControl(
    "ContinuousLaneChange",
    tr("ContinuousLaneChange"),
    tr("ContinuousLaneChange"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(continuouslanechange);
  toggles["ContinuousLaneChange"] = continuouslanechange;

  list->addItem(new LabelControl(tr("ContinuousLaneChangeCnt")));
  continuouslanechangecnt = new ContinuousLaneChangeCnt();
  connect(continuouslanechangecnt, &SPOptionControl::updateLabels, continuouslanechangecnt, &ContinuousLaneChangeCnt::refresh);
  list->addItem(continuouslanechangecnt);

  list->addItem(new LabelControl(tr("ContinuousLaneChangeInterval")));
  continuouslanechangeinterval = new ContinuousLaneChangeInterval();
  connect(continuouslanechangeinterval, &SPOptionControl::updateLabels, continuouslanechangeinterval, &ContinuousLaneChangeInterval::refresh);
  list->addItem(continuouslanechangeinterval);

  list->addItem(horizontal_line());
  //============================================================

  list->addItem(new LabelControl(tr("RoadType")));
  roadtype = new RoadType();
  connect(roadtype, &SPOptionControl::updateLabels, roadtype, &RoadType::refresh);
  list->addItem(roadtype);

  list->addItem(new LabelControl(tr("LaneStabTime")));
  lanestabtime = new LaneStabTime();
  connect(lanestabtime, &SPOptionControl::updateLabels, lanestabtime, &LaneStabTime::refresh);
  list->addItem(lanestabtime);

  list->addItem(new LabelControl(tr("BsdDelayTime")));
  bsddelaytime = new BsdDelayTime();
  connect(bsddelaytime, &SPOptionControl::updateLabels, bsddelaytime, &BsdDelayTime::refresh);
  list->addItem(bsddelaytime);

  list->addItem(new LabelControl(tr("SideBsdDelayTime")));
  sidebsddelaytime = new SideBsdDelayTime();
  connect(sidebsddelaytime, &SPOptionControl::updateLabels, sidebsddelaytime, &SideBsdDelayTime::refresh);
  list->addItem(sidebsddelaytime);

  list->addItem(new LabelControl(tr("SideRelDistTime")));
  sidereldisttime = new SideRelDistTime();
  connect(sidereldisttime, &SPOptionControl::updateLabels, sidereldisttime, &SideRelDistTime::refresh);
  list->addItem(sidereldisttime);

  list->addItem(new LabelControl(tr("SidevRelDistTime")));
  sidevreldisttime = new SidevRelDistTime();
  connect(sidevreldisttime, &SPOptionControl::updateLabels, sidevreldisttime, &SidevRelDistTime::refresh);
  list->addItem(sidevreldisttime);

  list->addItem(new LabelControl(tr("SideRadarMinDist")));
  sideradarmindist = new SideRadarMinDist();
  connect(sideradarmindist, &SPOptionControl::updateLabels, sideradarmindist, &SideRadarMinDist::refresh);
  list->addItem(sideradarmindist);

  list->addItem(horizontal_line());
  //============================================================
  list->addItem(new LabelControl(tr("HighWay Setting")));

  list->addItem(new LabelControl(tr("AutoForkDistOffsetH")));
  autoforkdistoffseth = new AutoForkDistOffsetH();
  connect(autoforkdistoffseth, &SPOptionControl::updateLabels, autoforkdistoffseth, &AutoForkDistOffsetH::refresh);
  list->addItem(autoforkdistoffseth);

  list->addItem(new LabelControl(tr("AutoDoForkDecalDistH")));
  autodoforkdecaldisth = new AutoDoForkDecalDistH();
  connect(autodoforkdecaldisth, &SPOptionControl::updateLabels, autodoforkdecaldisth, &AutoDoForkDecalDistH::refresh);
  list->addItem(autodoforkdecaldisth);

  list->addItem(new LabelControl(tr("AutoForkDecalRateH")));
  autoforkdecalrateh = new AutoForkDecalRateH();
  connect(autoforkdecalrateh, &SPOptionControl::updateLabels, autoforkdecalrateh, &AutoForkDecalRateH::refresh);
  list->addItem(autoforkdecalrateh);

  list->addItem(new LabelControl(tr("AutoForkSpeedMinH")));
  autoforkspeedminh = new AutoForkSpeedMinH();
  connect(autoforkspeedminh, &SPOptionControl::updateLabels, autoforkspeedminh, &AutoForkSpeedMinH::refresh);
  list->addItem(autoforkspeedminh);

  list->addItem(new LabelControl(tr("AutoDoForkBlinkerDistH")));
  autodoforkblinkerdisth = new AutoDoForkBlinkerDistH();
  connect(autodoforkblinkerdisth, &SPOptionControl::updateLabels, autodoforkblinkerdisth, &AutoDoForkBlinkerDistH::refresh);
  list->addItem(autodoforkblinkerdisth);

  list->addItem(new LabelControl(tr("AutoDoForkNavDistH")));
  autodoforknavdisth = new AutoDoForkNavDistH();
  connect(autodoforknavdisth, &SPOptionControl::updateLabels, autodoforknavdisth, &AutoDoForkNavDistH::refresh);
  list->addItem(autodoforknavdisth);

  list->addItem(new LabelControl(tr("AutoKeepForkSpeedH")));
  autokeepforkspeedh = new AutoKeepForkSpeedH();
  connect(autokeepforkspeedh, &SPOptionControl::updateLabels, autokeepforkspeedh, &AutoKeepForkSpeedH::refresh);
  list->addItem(autokeepforkspeedh);

  list->addItem(new LabelControl(tr("AutoEnTurnNewLaneTimeH")));
  autoenturnnewlanetimeh = new AutoEnTurnNewLaneTimeH();
  connect(autoenturnnewlanetimeh, &SPOptionControl::updateLabels, autoenturnnewlanetimeh, &AutoEnTurnNewLaneTimeH::refresh);
  list->addItem(autoenturnnewlanetimeh);

  auto autouphighwayroadlimit = new ParamControl(
    "AutoUpHighwayRoadLimit",
    tr("AutoUpHighwayRoadLimit"),
    tr("AutoUpHighwayRoadLimit"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(autouphighwayroadlimit);
  toggles["AutoUpHighwayRoadLimit"] = autouphighwayroadlimit;

  autouphighwayroadlimit40kmh = new AutoUpHighwayRoadLimit40KMH();
  connect(autouphighwayroadlimit40kmh, &SPOptionControl::updateLabels, autouphighwayroadlimit40kmh, &AutoUpHighwayRoadLimit40KMH::refresh);
  list->addItem(autouphighwayroadlimit40kmh);

  list->addItem(horizontal_line());
  //========================================================================
  list->addItem(new LabelControl(tr("Road Setting")));

  list->addItem(new LabelControl(tr("AutoForkDistOffset")));
   autoforkdistoffset = new AutoForkDistOffset();
  connect(autoforkdistoffset, &SPOptionControl::updateLabels, autoforkdistoffset, &AutoForkDistOffset::refresh);
  list->addItem(autoforkdistoffset);

  list->addItem(new LabelControl(tr("AutoDoForkDecalDist")));
  autodoforkdecaldist = new AutoDoForkDecalDist();
  connect(autodoforkdecaldist, &SPOptionControl::updateLabels, autodoforkdecaldist, &AutoDoForkDecalDist::refresh);
  list->addItem(autodoforkdecaldist);

  list->addItem(new LabelControl(tr("AutoForkDecalRate")));
  autoforkdecalrate = new AutoForkDecalRate();
  connect(autoforkdecalrate, &SPOptionControl::updateLabels, autoforkdecalrate, &AutoForkDecalRate::refresh);
  list->addItem(autoforkdecalrate);

  list->addItem(new LabelControl(tr("AutoForkSpeedMin")));
  autoforkspeedmin = new AutoForkSpeedMin();
  connect(autoforkspeedmin, &SPOptionControl::updateLabels, autoforkspeedmin, &AutoForkSpeedMin::refresh);
  list->addItem(autoforkspeedmin);

  list->addItem(new LabelControl(tr("AutoDoForkBlinkerDist")));
  autodoforkblinkerdist = new AutoDoForkBlinkerDist();
  connect(autodoforkblinkerdist, &SPOptionControl::updateLabels, autodoforkblinkerdist, &AutoDoForkBlinkerDist::refresh);
  list->addItem(autodoforkblinkerdist);

  list->addItem(new LabelControl(tr("AutoDoForkNavDist")));
  autodoforknavdist = new AutoDoForkNavDist();
  connect(autodoforknavdist, &SPOptionControl::updateLabels, autodoforknavdist, &AutoDoForkNavDist::refresh);
  list->addItem(autodoforknavdist);

  list->addItem(new LabelControl(tr("AutoKeepForkSpeed")));
  autokeepforkspeed = new AutoKeepForkSpeed();
  connect(autokeepforkspeed, &SPOptionControl::updateLabels, autokeepforkspeed, &AutoKeepForkSpeed::refresh);
  list->addItem(autokeepforkspeed);

  list->addItem(new LabelControl(tr("AutoEnTurnNewLaneTime")));
  autoenturnnewlanetime = new AutoEnTurnNewLaneTime();
  connect(autoenturnnewlanetime, &SPOptionControl::updateLabels, autoenturnnewlanetime, &AutoEnTurnNewLaneTime::refresh);
  list->addItem(autoenturnnewlanetime);

  auto autouproadlimit = new ParamControl(
    "AutoUpRoadLimit",
    tr("AutoUpRoadLimit"),
    tr("AutoUpRoadLimit"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(autouproadlimit);
  toggles["AutoUpRoadLimit"] = autouproadlimit;

  autouproadlimit40kmh = new AutoUpRoadLimit40KMH();
  connect(autouproadlimit40kmh, &SPOptionControl::updateLabels, autouproadlimit40kmh, &AutoUpRoadLimit40KMH::refresh);
  list->addItem(autouproadlimit40kmh);

  list->addItem(horizontal_line());
  //============================================================

  list->addItem(new LabelControl(tr("AutoCurveSpeedFactorH")));
  autocurvespeedfactorh = new AutoCurveSpeedFactorH();
  connect(autocurvespeedfactorh, &SPOptionControl::updateLabels, autocurvespeedfactorh, &AutoCurveSpeedFactorH::refresh);
  list->addItem(autocurvespeedfactorh);

  list->addItem(new LabelControl(tr("AutoCurveSpeedAggressivenessH")));
  autocurvespeedaggressivenessh = new AutoCurveSpeedAggressivenessH();
  connect(autocurvespeedaggressivenessh, &SPOptionControl::updateLabels, autocurvespeedaggressivenessh, &AutoCurveSpeedAggressivenessH::refresh);
  list->addItem(autocurvespeedaggressivenessh);

  list->addItem(new LabelControl(tr("AutoCurveSpeedFactor")));
  autocurvespeedfactor = new AutoCurveSpeedFactor();
  connect(autocurvespeedfactor, &SPOptionControl::updateLabels, autocurvespeedfactor, &AutoCurveSpeedFactor::refresh);
  list->addItem(autocurvespeedfactor);

  list->addItem(new LabelControl(tr("AutoCurveSpeedAggressiveness")));
  autocurvespeedaggressiveness = new AutoCurveSpeedAggressiveness();
  connect(autocurvespeedaggressiveness, &SPOptionControl::updateLabels, autocurvespeedaggressiveness, &AutoCurveSpeedAggressiveness::refresh);
  list->addItem(autocurvespeedaggressiveness);

  list->addItem(horizontal_line());
  //============================================================

  auto turntolanechange = new ParamControl(
    "TurnToLaneChange",
    tr("TurnToLaneChange"),
    tr("TurnToLaneChange"),
    "../assets/offroad/icon_blank.png",
    this
  );
  list->addItem(turntolanechange);
  toggles["TurnToLaneChange"] = turntolanechange;

  list->addItem(new LabelControl(tr("CpSpdAndRoadLimit")));
  cpspdandroadlimit = new CpSpdAndRoadLimit();
  connect(cpspdandroadlimit, &SPOptionControl::updateLabels, cpspdandroadlimit, &CpSpdAndRoadLimit::refresh);
  list->addItem(cpspdandroadlimit);

  list->addItem(horizontal_line());
  //============================================================

  param_watcher = new ParamWatcher(this);
  QObject::connect(param_watcher, &ParamWatcher::paramChanged, [=](const QString &param_name, const QString &param_value) {
    updateToggles();
  });

  navScreen = new QWidget(this);
  QVBoxLayout* vlayout = new QVBoxLayout(navScreen);
  vlayout->setContentsMargins(50, 20, 50, 20);

  scrollView = new ScrollView(list, this);
  vlayout->addWidget(scrollView, 1);
  main_layout->addWidget(navScreen);

  main_layout->setCurrentWidget(navScreen);
}

/**************************************************************/
AutoForkDistOffsetH::AutoForkDistOffsetH() : SPOptionControl(
  "AutoForkDistOffsetH",
  "",
  tr("AutoForkDistOffsetH"),
  "../assets/offroad/icon_blank.png",
  {0, 5000},
  5) {

  refresh();
}
void AutoForkDistOffsetH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkDistOffsetH"));
  setLabel(option + " m");
}

AutoDoForkDecalDistH::AutoDoForkDecalDistH() : SPOptionControl(
  "AutoDoForkDecalDistH",
  "",
  tr("AutoDoForkDecalDistH"),
  "../assets/offroad/icon_blank.png",
  {0, 500},
  5) {

  refresh();
}
void AutoDoForkDecalDistH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkDecalDistH"));
  setLabel(option + " m");
}

AutoForkDecalRateH::AutoForkDecalRateH() : SPOptionControl(
  "AutoForkDecalRateH",
  "",
  tr("AutoForkDecalRateH"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void AutoForkDecalRateH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkDecalRateH"));
  setLabel(option + " %");
}

AutoForkSpeedMinH::AutoForkSpeedMinH() : SPOptionControl(
  "AutoForkSpeedMinH",
  "",
  tr("AutoForkSpeedMinH"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoForkSpeedMinH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkSpeedMinH"));
  setLabel(option + " km/h");
}

AutoDoForkBlinkerDistH::AutoDoForkBlinkerDistH() : SPOptionControl(
  "AutoDoForkBlinkerDistH",
  "",
  tr("AutoDoForkBlinkerDistH"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoDoForkBlinkerDistH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkBlinkerDistH"));
  setLabel(option + " m");
}

AutoDoForkNavDistH::AutoDoForkNavDistH() : SPOptionControl(
  "AutoDoForkNavDistH",
  "",
  tr("AutoDoForkNavDistH"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoDoForkNavDistH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkNavDistH"));
  setLabel(option + " m");
}

AutoKeepForkSpeedH::AutoKeepForkSpeedH() : SPOptionControl(
  "AutoKeepForkSpeedH",
  "",
  tr("AutoKeepForkSpeedH"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoKeepForkSpeedH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoKeepForkSpeedH"));
  setLabel(option + " s");
}

AutoEnTurnNewLaneTimeH::AutoEnTurnNewLaneTimeH() : SPOptionControl(
  "AutoEnTurnNewLaneTimeH",
  "",
  tr("AutoEnTurnNewLaneTimeH"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoEnTurnNewLaneTimeH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoEnTurnNewLaneTimeH"));
  setLabel(option + " s");
}

AutoUpHighwayRoadLimit40KMH::AutoUpHighwayRoadLimit40KMH() : SPOptionControl(
  "AutoUpHighwayRoadLimit40KMH",
  "",
  tr("AutoUpHighwayRoadLimit40KMH"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoUpHighwayRoadLimit40KMH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoUpHighwayRoadLimit40KMH"));
  setLabel(option + " km/h");
}

/**************************************************************/
AutoForkDistOffset::AutoForkDistOffset() : SPOptionControl(
  "AutoForkDistOffset",
  "",
  tr("AutoForkDistOffset"),
  "../assets/offroad/icon_blank.png",
  {0, 5000},
  5) {

  refresh();
}
void AutoForkDistOffset::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkDistOffset"));
  setLabel(option + " m");
}

AutoDoForkDecalDist::AutoDoForkDecalDist() : SPOptionControl(
  "AutoDoForkDecalDist",
  "",
  tr("AutoDoForkDecalDist"),
  "../assets/offroad/icon_blank.png",
  {0, 500},
  5) {

  refresh();
}
void AutoDoForkDecalDist::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkDecalDist"));
  setLabel(option + " m");
}

AutoForkDecalRate::AutoForkDecalRate() : SPOptionControl(
  "AutoForkDecalRate",
  "",
  tr("AutoForkDecalRate"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void AutoForkDecalRate::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkDecalRate"));
  setLabel(option + " %");
}

AutoForkSpeedMin::AutoForkSpeedMin() : SPOptionControl(
  "AutoForkSpeedMin",
  "",
  tr("AutoForkSpeedMin"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoForkSpeedMin::refresh() {
  QString option = QString:: fromStdString(params.get("AutoForkSpeedMin"));
  setLabel(option + " km/h");
}

AutoDoForkBlinkerDist::AutoDoForkBlinkerDist() : SPOptionControl(
  "AutoDoForkBlinkerDist",
  "",
  tr("AutoDoForkBlinkerDist"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoDoForkBlinkerDist::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkBlinkerDist"));
  setLabel(option + " m");
}

AutoDoForkNavDist::AutoDoForkNavDist() : SPOptionControl(
  "AutoDoForkNavDist",
  "",
  tr("AutoDoForkNavDist"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoDoForkNavDist::refresh() {
  QString option = QString:: fromStdString(params.get("AutoDoForkNavDist"));
  setLabel(option + " m");
}

AutoKeepForkSpeed::AutoKeepForkSpeed() : SPOptionControl(
  "AutoKeepForkSpeed",
  "",
  tr("AutoKeepForkSpeed"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoKeepForkSpeed::refresh() {
  QString option = QString:: fromStdString(params.get("AutoKeepForkSpeed"));
  setLabel(option + " s");
}

AutoEnTurnNewLaneTime::AutoEnTurnNewLaneTime() : SPOptionControl(
  "AutoEnTurnNewLaneTime",
  "",
  tr("AutoEnTurnNewLaneTime"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoEnTurnNewLaneTime::refresh() {
  QString option = QString:: fromStdString(params.get("AutoEnTurnNewLaneTime"));
  setLabel(option + " s");
}

AutoUpRoadLimit40KMH::AutoUpRoadLimit40KMH() : SPOptionControl(
  "AutoUpRoadLimit40KMH",
  "",
  tr("AutoUpRoadLimit40KMH"),
  "../assets/offroad/icon_blank.png",
  {0, 60},
  1) {

  refresh();
}
void AutoUpRoadLimit40KMH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoUpRoadLimit40KMH"));
  setLabel(option + " km/h");
}

/**************************************************************/
ContinuousLaneChangeCnt::ContinuousLaneChangeCnt() : SPOptionControl(
  "ContinuousLaneChangeCnt",
  "",
  tr("ContinuousLaneChangeCnt"),
  "../assets/offroad/icon_blank.png",
  {-1, 10},
  1) {

  refresh();
}
void ContinuousLaneChangeCnt::refresh() {
  QString option = QString:: fromStdString(params.get("ContinuousLaneChangeCnt"));
  setLabel(option);
}

ContinuousLaneChangeInterval::ContinuousLaneChangeInterval() : SPOptionControl(
  "ContinuousLaneChangeInterval",
  "",
  tr("ContinuousLaneChangeInterval"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void ContinuousLaneChangeInterval::refresh() {
  QString option = QString:: fromStdString(params.get("ContinuousLaneChangeInterval"));
  setLabel(option + " s");
}

LaneStabTime::LaneStabTime() : SPOptionControl(
  "LaneStabTime",
  "",
  tr("LaneStabTime"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void LaneStabTime::refresh() {
  QString option = QString:: fromStdString(params.get("LaneStabTime"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " 秒");  // 保留1位小数
  } else {
    setLabel(option + " s");  // 如果转换失败，直接显示原值
  }
}

BsdDelayTime::BsdDelayTime() : SPOptionControl(
  "BsdDelayTime",
  "",
  tr("BsdDelayTime"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void BsdDelayTime::refresh() {
  QString option = QString:: fromStdString(params.get("BsdDelayTime"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " 秒");  // 保留1位小数
  } else {
    setLabel(option + " s");  // 如果转换失败，直接显示原值
  }
}

SideBsdDelayTime::SideBsdDelayTime() : SPOptionControl(
  "SideBsdDelayTime",
  "",
  tr("SideBsdDelayTime"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void SideBsdDelayTime::refresh() {
  QString option = QString:: fromStdString(params.get("SideBsdDelayTime"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " 秒");  // 保留1位小数
  } else {
    setLabel(option + " s");  // 如果转换失败，直接显示原值
  }
}

SideRelDistTime::SideRelDistTime() : SPOptionControl(
  "SideRelDistTime",
  "",
  tr("SideRelDistTime"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void SideRelDistTime::refresh() {
  QString option = QString:: fromStdString(params.get("SideRelDistTime"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " 秒");  // 保留1位小数
  } else {
    setLabel(option + " s");  // 如果转换失败，直接显示原值
  }
}

SidevRelDistTime::SidevRelDistTime() : SPOptionControl(
  "SidevRelDistTime",
  "",
  tr("SidevRelDistTime"),
  "../assets/offroad/icon_blank.png",
  {0, 100},
  1) {

  refresh();
}
void SidevRelDistTime::refresh() {
  QString option = QString:: fromStdString(params.get("SidevRelDistTime"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " 秒");  // 保留1位小数
  } else {
    setLabel(option + " s");  // 如果转换失败，直接显示原值
  }
}

SideRadarMinDist::SideRadarMinDist() : SPOptionControl(
  "SideRadarMinDist",
  "",
  tr("SideRadarMinDist"),
  "../assets/offroad/icon_blank.png",
  {-200, 200},
  1) {

  refresh();
}
void SideRadarMinDist::refresh() {
  QString option = QString:: fromStdString(params.get("SideRadarMinDist"));
  bool ok;
  int int_value = option.toInt(&ok);
  if (ok) {
    double real_value = int_value / 10.0;  // 假设是除以10
    setLabel(QString::number(real_value, 'f', 1) + " m");  // 保留1位小数
  } else {
    setLabel(option + " m");  // 如果转换失败，直接显示原值
  }
}

////////////////////////////////////////////////////////////////////////////////
AutoCurveSpeedFactorH::AutoCurveSpeedFactorH() : SPOptionControl(
  "AutoCurveSpeedFactorH",
  "",
  tr("AutoCurveSpeedFactorH"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoCurveSpeedFactorH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoCurveSpeedFactorH"));
  setLabel(option + " %");
}

AutoCurveSpeedAggressivenessH::AutoCurveSpeedAggressivenessH() : SPOptionControl(
  "AutoCurveSpeedAggressivenessH",
  "",
  tr("AutoCurveSpeedAggressivenessH"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoCurveSpeedAggressivenessH::refresh() {
  QString option = QString:: fromStdString(params.get("AutoCurveSpeedAggressivenessH"));
  setLabel(option + " %");
}

AutoCurveSpeedFactor::AutoCurveSpeedFactor() : SPOptionControl(
  "AutoCurveSpeedFactor",
  "",
  tr("AutoCurveSpeedFactor"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoCurveSpeedFactor::refresh() {
  QString option = QString:: fromStdString(params.get("AutoCurveSpeedFactor"));
  setLabel(option + " %");
}

AutoCurveSpeedAggressiveness::AutoCurveSpeedAggressiveness() : SPOptionControl(
  "AutoCurveSpeedAggressiveness",
  "",
  tr("AutoCurveSpeedAggressiveness"),
  "../assets/offroad/icon_blank.png",
  {0, 200},
  1) {

  refresh();
}
void AutoCurveSpeedAggressiveness::refresh() {
  QString option = QString:: fromStdString(params.get("AutoCurveSpeedAggressiveness"));
  setLabel(option + " %");
}

CpSpdAndRoadLimit::CpSpdAndRoadLimit() : SPOptionControl(
  "CpSpdAndRoadLimit",
  "",
  tr("CpSpdAndRoadLimit"),
  "../assets/offroad/icon_blank.png",
  {0, 2},
  1) {

  refresh();
}
void CpSpdAndRoadLimit::refresh() {
  QString option = QString:: fromStdString(params.get("CpSpdAndRoadLimit"));
  setLabel(option);
}

RoadType::RoadType() : SPOptionControl(
  "RoadType",
  "",
  tr("RoadType"),
  "../assets/offroad/icon_blank.png",
  {-10, 100},
  1) {

  refresh();
}
void RoadType::refresh() {
  QString option = QString:: fromStdString(params.get("RoadType"));
  setLabel(option);
}
