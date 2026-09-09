<template>
  <div class="rating-form">
    <h3>امتیازدهی به برنامه زمانی</h3>

    <div v-for="schedule in schedules" :key="schedule.id" class="schedule-item">
      <h4>{{ schedule.title }}</h4>
      <p>{{ schedule.description }}</p>

      <div class="rating-options">
        <label v-for="option in ratingOptions" :key="option.value">
          <input type="radio" :value="option.value" v-model="selectedRating[schedule.id]" />
          {{ option.label }}
        </label>
      </div>

      <div class="form-group">
        <textarea v-model="comments[schedule.id]" placeholder="نظر شما (اختیاری)"></textarea>
      </div>

      <button @click="submitRating(schedule.id)" :disabled="loading">ثبت امتیاز</button>
    </div>

    <p v-if="message" class="message">{{ message }}</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      schedules: [],
      selectedRating: {},
      comments: {},
      loading: false,
      message: '',
      ratingOptions: [
        { value: 'excellent', label: 'خیلی خوب' },
        { value: 'good', label: 'خوب' },
        { value: 'average', label: 'متوسط' },
        { value: 'weak', label: 'ضعیف' },
        { value: 'very_weak', label: 'خیلی ضعیف' }
      ]
    };
  },
  mounted() {
    this.fetchSchedules();
  },
  methods: {
    async fetchSchedules() {
      try {
        const res = await axios.get('/api/schedules');
        this.schedules = res.data;
      } catch (err) {
        console.error('Error fetching schedules:', err);
      }
    },
    async submitRating(scheduleId) {
      const rating = this.selectedRating[scheduleId];
      if (!rating) {
        this.message = 'لطفاً یک امتیاز انتخاب کنید';
        return;
      }

      this.loading = true;
      this.message = '';
      try {
        const studentId = 1; // از احراز هویت دریافت شود
        await axios.post('/api/ratings', {
          schedule_id: scheduleId,
          rating: rating,
          comment: this.comments[scheduleId] || ''
        }, { params: { student_id: studentId } });
        this.message = 'امتیاز شما با موفقیت ثبت شد!';
        this.selectedRating[scheduleId] = '';
        this.comments[scheduleId] = '';
      } catch (err) {
        this.message = 'خطا: ' + (err.response?.data?.detail || err.message);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>