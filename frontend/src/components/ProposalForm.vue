<template>
  <div class="proposal-form">
    <h3>پیشنهاد دروس برای ترم جدید</h3>
    <form @submit.prevent="submitProposal">
      <div class="form-group">
        <label>ترم:</label>
        <input v-model="term" type="text" placeholder="مثال: 1402-1" required />
      </div>

      <div class="form-group">
        <label>انتخاب دروس:</label>
        <div v-for="course in availableCourses" :key="course.id" class="course-item">
          <input type="checkbox" :value="course.id" v-model="selectedCourses" />
          <span>{{ course.name }} ({{ course.code }})</span>
        </div>
      </div>

      <div class="form-group">
        <label>توضیحات (اختیاری):</label>
        <textarea v-model="description" rows="3"></textarea>
      </div>

      <button type="submit" :disabled="loading">ثبت پیشنهاد</button>
      <p v-if="message" class="message">{{ message }}</p>
    </form>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      term: '',
      selectedCourses: [],
      description: '',
      availableCourses: [],
      loading: false,
      message: ''
    };
  },
  mounted() {
    this.fetchCourses();
  },
  methods: {
    async fetchCourses() {
      try {
        const res = await axios.get('/api/courses');
        this.availableCourses = res.data;
      } catch (err) {
        console.error('Error fetching courses:', err);
      }
    },
    async submitProposal() {
      if (this.selectedCourses.length === 0) {
        this.message = 'حداقل یک درس را انتخاب کنید';
        return;
      }
      this.loading = true;
      this.message = '';
      try {
        const studentId = 1; // از احراز هویت دریافت شود
        await axios.post('/api/proposals', {
          term: this.term,
          course_ids: this.selectedCourses,
          description: this.description
        }, { params: { student_id: studentId } });
        this.message = 'پیشنهاد با موفقیت ثبت شد!';
        this.term = '';
        this.selectedCourses = [];
        this.description = '';
      } catch (err) {
        this.message = 'خطا در ثبت پیشنهاد: ' + (err.response?.data?.detail || err.message);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>