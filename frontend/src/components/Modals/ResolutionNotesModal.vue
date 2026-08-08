<template>
  <Dialog v-model:open="show" :title="modalTitle" @close="cancel">
    <template #default>
      <div class="-mt-3 mb-4 text-p-base text-ink-gray-7">
        {{ modalDescription }}
      </div>
      <div class="flex flex-col gap-3">
        <!-- Lost Reason (only for Approved status - losing the student) -->
        <div v-if="isApproved">
          <div class="mb-2 text-sm text-ink-gray-5">
            {{ __('Refund Reason') }}
            <span class="text-ink-red-5">*</span>
          </div>
          <Link
            ref="linkRef"
            class="form-control flex-1 truncate"
            :value="lostReason"
            doctype="CRM Lost Reason"
            :onCreate="onCreate"
            @change="(v) => (lostReason = v)"
          />
        </div>
        <!-- Resolution Notes (required for both) -->
        <div>
          <div class="mb-2 text-sm text-ink-gray-5">
            {{ notesLabel }}
            <span class="text-ink-red-5">*</span>
          </div>
          <FormControl
            class="form-control flex-1 truncate"
            type="textarea"
            :rows="4"
            :value="resolutionNotes"
            :placeholder="notesPlaceholder"
            @change="(e) => (resolutionNotes = e.target.value)"
          />
        </div>
        <!-- Additional Notes (only for Approved with Other reason) -->
        <div v-if="isApproved && lostReason === 'Other'">
          <div class="mb-2 text-sm text-ink-gray-5">
            {{ __('Additional Notes') }}
            <span class="text-ink-red-5">*</span>
          </div>
          <FormControl
            class="form-control flex-1 truncate"
            type="textarea"
            :value="lostNotes"
            :placeholder="__('Provide additional details for Other reason...')"
            @change="(e) => (lostNotes = e.target.value)"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-between items-center gap-2">
        <div><ErrorMessage :message="error" /></div>
        <div class="flex gap-2">
          <Button :label="__('Cancel')" @click="cancel" />
          <Button variant="solid" :label="__('Save')" @click="save" />
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import Link from '@/components/Controls/Link.vue'
import { createDocument } from '@/composables/document'
import { Dialog } from 'frappe-ui'
import { ref, computed } from 'vue'

const props = defineProps({
  doctype: { type: String, default: 'CRM Deal' },
  document: { type: Object, required: true },
  statusType: { type: String, required: true }, // 'Won' or 'Lost'
})

const show = defineModel({ type: Boolean })

const linkRef = ref(null)
const doc = props.document.doc
const resolutionNotes = ref(doc.resolution_notes || '')
const lostReason = ref(doc.lost_reason || '')
const lostNotes = ref(doc.lost_notes || '')
const error = ref('')

const isRejected = computed(() => props.statusType === 'Lost')
const isApproved = computed(() => props.statusType === 'Won')

const modalTitle = computed(() => {
  if (isApproved.value) return __('Approve Refund')
  return __('Reject Refund')
})

const modalDescription = computed(() => {
  if (isApproved.value) {
    return __('Approving this refund means losing this student. Please provide the refund reason and notes.')
  }
  return __('Please provide the reason for rejecting this refund request.')
})

const notesLabel = computed(() => {
  if (isApproved.value) return __('Approval Notes')
  return __('Rejection Notes')
})

const notesPlaceholder = computed(() => {
  if (isApproved.value) {
    return __('Enter approval notes, refund amount confirmed, etc.')
  }
  return __('Enter reason for rejecting this refund request...')
})

function cancel() {
  show.value = false
  error.value = ''
  resolutionNotes.value = ''
  lostReason.value = ''
  lostNotes.value = ''
  doc.status = props.document.originalDoc.status
}

function save() {
  // Validate resolution notes (required for both)
  if (!resolutionNotes.value) {
    error.value = isApproved.value
      ? __('Approval Notes are required')
      : __('Rejection Notes are required')
    return
  }

  // Validate lost reason for Approved status (losing the student)
  if (isApproved.value && !lostReason.value) {
    error.value = __('Refund Reason is required')
    return
  }

  // Validate additional notes if reason is Other
  if (isApproved.value && lostReason.value === 'Other' && !lostNotes.value) {
    error.value = __('Additional Notes are required when Refund Reason is "Other"')
    return
  }

  error.value = ''
  show.value = false

  doc.resolution_notes = resolutionNotes.value
  if (isApproved.value) {
    doc.lost_reason = lostReason.value
    doc.lost_notes = lostNotes.value
  }
  props.document.save.submit()
}

function onCreate(value, close) {
  let doc = { lost_reason: value }
  createDocument('CRM Lost Reason', doc, close, (doc) => {
    lostReason.value = doc.name
    linkRef.value?.reload('', true)
  })
}
</script>
