// frontend/src/pages/SchedulePages.jsx
import React from "react";
import BasketPage from "./BasketPage";
import InstructorTimePage from "./InstructorTimePage";
import RoomAllocationPage from "./RoomAllocationPage";
import OptimizationPage from "./OptimizationPage";
import LegacySchedulePage from "./LegacySchedulePage";

/**
 * کامپوننت اصلی صفحات فرایند زمان‌بندی
 * بر اساس activePage، صفحه متناسب را رندر می‌کند
 */
export default function SchedulePages({
  activePage,
  semester,
  setSemester,
  levels,
  uniqueCourses,
  termCourses,
  offeredCourses,
  basketData,
  instructorTimeData,
  roomAllocationData,
  optimizedData,
  processLoading,
  onBasketComplete,
  onBasketCreated,
  basketId,
  onProcessSchedule,
  onProcessRooms,
  onProcessOptimize,
  onClearSchedule,
  onClearRooms,
  onClearOptimize,
  schedule,
  rankedCourses,
  loading,
  onGenerate,
  workflowId,
  workflowSteps,
  currentStep,
  workflowLoading,
  onStartWorkflow,
  onNextStep,
  onPrevStep,
  onFinalize,
  onUpdateStepData,
  teachingPreferences = [],
  timePreferences = [],
  onNextToRooms = null,
  onNextToOptimization = null,
  onManualAssignComplete = null,
  onNavigateToBasketList = null,
  // ===== Prop جدید برای همگام‌سازی داده‌های زمان‌بندی =====
  onInstructorDataLoaded = null,
}) {
  switch (activePage) {
    case "basket":
      return (
        <BasketPage
          semester={semester}
          levels={levels}
          onComplete={onBasketComplete}
          loading={processLoading}
          uniqueCourses={uniqueCourses}
          termCourses={termCourses}
          workflowId={workflowId}
          basketId={basketId}
          onBasketCreated={onBasketCreated}
          basketData={basketData}
        />
      );

    case "instructor-time":
      return (
        <InstructorTimePage
          basketData={basketData}
          instructorTimeData={instructorTimeData}
          onProcess={onProcessSchedule}
          onClear={onClearSchedule}
          loading={processLoading}
          onNext={onNextToRooms || (() => {})}
          workflowId={workflowId}
          teachingPreferences={teachingPreferences}
          timePreferences={timePreferences}
          basketId={basketId}
          onManualAssignComplete={onManualAssignComplete}
          onNavigateToBasketList={onNavigateToBasketList}
        />
      );

    case "room-allocation":
      return (
        <RoomAllocationPage
          instructorTimeData={instructorTimeData}
          roomAllocationData={roomAllocationData}
          onProcess={onProcessRooms}
          onClear={onClearRooms}
          loading={processLoading}
          onNext={onNextToOptimization || (() => {})}
          basketId={basketId}
          workflowId={workflowId}
          // ===== ارسال prop جدید به RoomAllocationPage =====
          onInstructorDataLoaded={onInstructorDataLoaded}
        />
      );

    case "optimization":
      return (
        <OptimizationPage
          roomAllocationData={roomAllocationData}
          optimizedData={optimizedData}
          onProcess={onProcessOptimize}
          onClear={onClearOptimize}
          loading={processLoading}
          onNext={() => {}}
          basketId={basketId}
        />
      );

    case "schedule":
      return (
        <LegacySchedulePage
          semester={semester}
          setSemester={setSemester}
          levels={levels}
          schedule={schedule}
          rankedCourses={rankedCourses}
          loading={loading}
          onGenerate={onGenerate}
          workflowId={workflowId}
          workflowSteps={workflowSteps}
          currentStep={currentStep}
          workflowLoading={workflowLoading}
          onStartWorkflow={onStartWorkflow}
          onNextStep={onNextStep}
          onPrevStep={onPrevStep}
          onFinalize={onFinalize}
          onUpdateStepData={onUpdateStepData}
        />
      );

    default:
      return <div className="empty-state">صفحه‌ای یافت نشد</div>;
  }
}