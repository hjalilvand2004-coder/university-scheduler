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
  onBasketCreated,        // جدید: برای دریافت شناسه سبد از BasketPage
  basketId,              // جدید: شناسه سبد فعلی برای ارسال به BasketPage و سایر صفحات
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
  // ===== Props مورد نیاز برای InstructorTimePage =====
  teachingPreferences = [],
  timePreferences = [],
  // ===== Prop جدید برای رفتن به صفحه تخصیص اتاق =====
  onNextToRooms = null,
  // ===== Props اضافی برای تخصیص اتاق و بهینه‌سازی (در صورت نیاز) =====
  onManualAssignComplete = null,
  // ===== Prop جدید برای هدایت به لیست سبدها (از InstructorTimePage) =====
  onNavigateToBasketList = null,
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
          onNavigateToBasketList={onNavigateToBasketList} // <-- اضافه شد
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
          onNext={() => {}}
          basketId={basketId}
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