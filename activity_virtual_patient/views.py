from StdSuites.Type_Names_Suite import null
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import render_to_response
from django.template import Context, loader, Context, loader
from django.utils import simplejson
from tobaccocessation.activity_virtual_patient.models import *
from django.db.models import Q

@login_required
def root(request):
    # dump the user back where they were when they left
    user_state = _get_user_state(request)
    
    if (user_state.has_key('path')):
        url = user_state['path']
    else:
        url = '/activity/virtualpatient/options/1'
    
    return HttpResponseRedirect(url)

@login_required        
def load(request, page_id, patient_id):
    user_state = _get_user_state(request)
    
    doc = {}
    if patient_id in user_state['patients']:
        doc = user_state['patients'][patient_id]

    return HttpResponse(simplejson.dumps(doc), 'application/json')

@login_required
def save(request, page_id, patient_id):
    _save_user_state(request, patient_id)
    doc = { 'success': '1' }
    return HttpResponse(simplejson.dumps(doc), 'application/json')

@login_required
def navigate(request, page_id, patient_id):
    _save_user_state(request, patient_id)
    
    next_page = _get_next_page(page_id)
    
    doc = {}
    doc['redirect'] = reverse(next_page, args=[patient_id])
    return HttpResponse(simplejson.dumps(doc), 'application/json')

@login_required
def options(request, patient_id):
    _save_my_place(request)
    
    previous_url = ""
    prev_patient = _get_previous_patient(patient_id)
    if (prev_patient):
        previous_url = reverse('results', args=[prev_patient.id])
    
    ctx = Context({
       'user': request.user,
       'patient': Patient.objects.get(id=patient_id),
       'medications': Medication.objects.all().order_by('display_order'),
       'page_id': "options",
       'previous_url': previous_url
    })
        
    template = loader.get_template('activity_virtual_patient/options.html')
    return HttpResponse(template.render(ctx))

@login_required
def selection(request, patient_id):
    _save_my_place(request)
    
    ctx = Context({
       'user': request.user,
       'patient': Patient.objects.get(id=patient_id),
       'medications': Medication.objects.all().order_by('display_order'),
       'page_id': "selection",
    })
        
    template = loader.get_template('activity_virtual_patient/selection.html')
    return HttpResponse(template.render(ctx))
    
@login_required
def prescription(request, patient_id, medication_idx='0'):
    _save_my_place(request)
    
    user_state = _get_user_state(request)
    idx = int(medication_idx)
    
    if (idx == 0):
        previous_url = reverse('selection', args=[patient_id])
    else:
        previous_url = reverse('next_prescription', args=[patient_id, '0'])
        
    if (_is_combination(user_state, patient_id)):
        tag = user_state['patients'][patient_id]['combination'][idx]
    else:
        tag = user_state['patients'][patient_id]['prescribe']
        
    medication = Medication.objects.get(tag=tag)
    
    # this is an ugly little workaround due to the django template ifequal tag
    # i was trying to compare a Model.id property with the stored json selection which is a string by default
    # with no way to cast in the templates, I have to specifically send down ints to the template to 
    # get this to work. Django's templates may be a little too crippled for my tastes...
    dosage_idx = -1
    concentration_idx = -1
    refill_idx = -1
    dosage2_idx = -1
    concentration2_idx = -1
    refill2_idx = -1
    if (user_state['patients'][patient_id].has_key(tag)):
        rx = user_state['patients'][patient_id][tag]
        dosage_idx = int(rx['dosage'])
        concentration_idx = int(rx['concentration'])
        refill_idx = int(rx['refill'])
        
        if (medication.rx_count > 1):
            dosage2_idx = int(rx['dosage2'])
            concentration2_idx = int(rx['concentration2'])
            refill2_idx = int(rx['refill2'])
            
    
    ctx = Context({
       'user': request.user,
       'patient': Patient.objects.get(id=patient_id),
       'page_id': "prescription",
       'medication': medication,
       'medication_idx': medication_idx,
       'previous_url': previous_url,
       'dosage_idx': dosage_idx,
       'concentration_idx': concentration_idx,
       'refill_idx': refill_idx,
    })
        
    template = loader.get_template('activity_virtual_patient/prescription.html')
    return HttpResponse(template.render(ctx))

@login_required
def prescription_post(request):
    # the other views are using "navigate" for this functionality
    # it might be possible to remove the special casing here and localize it to other places.
    # e.g. the next/prev url can take place in get_next_page / get_prev_page
    
    user_state = _get_user_state(request)
    update = simplejson.loads(request.POST['json'])
    patient_id = update['patient_id']
    
    # save the data out
    medication_tag = update['medication_tag']
    user_state['patients'][patient_id][medication_tag] = update[medication_tag]
    _save(request, user_state)
    
    # navigate to the next view
    idx = int(update['medication_idx'])
    if (_is_combination(user_state, patient_id) and idx == 0):
        next_url = reverse('next_prescription', args=[patient_id, '1'])
    else:
        next_url = reverse('results', args=[patient_id])
            
    doc = {}
    doc['redirect'] = next_url
    return HttpResponse(simplejson.dumps(doc), 'application/json')
    
@login_required
def results(request, patient_id):
    _save_my_place(request)
    user_state = _get_user_state(request)
    patient_state = user_state['patients'][patient_id]
    prescription = None
    
    # pickup the feedback based on the user's answers
    # query for the treatment option the user selected based on the prescribed drugs
    # grade the user's rx(s)
    to = None
    correct_rx = False
    combination = False
    if (_is_combination(user_state, patient_id)):
        combination = True
        med_tag_one =  patient_state['combination'][0]
        med_tag_two =  patient_state['combination'][1]
        
        to = TreatmentOption.objects.get(Q(medication_one__tag=med_tag_one) | Q(medication_one__tag=med_tag_two), 
                                         Q(medication_two__tag=med_tag_one) | Q(medication_two__tag=med_tag_two),
                                         patient__id=patient_id) 
                                         
        cc1 = ConcentrationChoice.objects.get(id=patient_state[med_tag_one]['concentration'])
        cc2 = ConcentrationChoice.objects.get(id=patient_state[med_tag_two]['concentration'])
        dc1 = DosageChoice.objects.get(id=patient_state[med_tag_one]['dosage'])
        dc2 = DosageChoice.objects.get(id=patient_state[med_tag_two]['dosage'])
        
        rc1 = RefillChoice.objects.get(id=patient_state[med_tag_one]['refill'])
        rc2 = RefillChoice.objects.get(id=patient_state[med_tag_two]['refill'])
        
        prescription = "Combination: %s %s %s %s refills, %s %s %s %s refills" % (med_tag_one, cc1.concentration, dc1.dosage, rc1.refill, med_tag_two, cc2.concentration, dc2.dosage, rc2.refill) 
            
        correct_rx = cc1.correct and cc2.correct and dc1.correct and dc2.correct and rc1.correct and rc2.correct
    else:
        med_tag_one =  patient_state['prescribe']
        to = TreatmentOption.objects.get(patient__id=patient_id, medication_one__tag=med_tag_one, medication_two=None)
        cc1 = ConcentrationChoice.objects.get(id=patient_state[med_tag_one]['concentration'])
        dc1 = DosageChoice.objects.get(id=patient_state[med_tag_one]['dosage'])
        rc1 = RefillChoice.objects.get(id=patient_state[med_tag_one]['refill'])

        prescription = "%s %s %s %s" % (med_tag_one, cc1.concentration, dc1.dosage, rc1.refill)
        correct_rx = cc1.correct and dc1.correct and rc1.correct

    #todo - is there a better way to model this? 
    tf = TreatmentFeedback.objects.filter(patient__id=patient_id, classification=to.classification, correct_dosage=correct_rx)
    if (tf.count() > 1):
        tf = TreatmentFeedback.objects.filter(patient__id=patient_id, classification=to.classification, correct_dosage=correct_rx, combination_therapy=combination)
    
    if (_is_combination(user_state, patient_id)):
        previous_url = reverse('next_prescription', args=[patient_id, '1'])
    else:
        previous_url = reverse('next_prescription', args=[patient_id, '0'])
        
    next_url = None
    next_patient = _get_next_patient(patient_id)
    if (next_patient):
        next_url = reverse('options', args=[next_patient.id])

    ctx = Context({
       'user': request.user,
       'patient': Patient.objects.get(id=patient_id),
       'feedback': tf[0].feedback,
       'page_id': "results",
       'best_treatment_options': TreatmentOptionReasoning.objects.filter(patient__id=patient_id, classification__rank=1),
       'reasonable_treatment_options': TreatmentOptionReasoning.objects.filter(patient__id=patient_id, classification__rank=2),
       'ineffective_treatment_options': TreatmentOptionReasoning.objects.filter(patient__id=patient_id, classification__rank=3),
       'harmful_treatment_options': TreatmentOptionReasoning.objects.filter(patient__id=patient_id, classification__rank=4),
       'previous_url': previous_url,
       'next_url': next_url,
       'prescription': prescription
    })
        
    template = loader.get_template('activity_virtual_patient/results.html')
    return HttpResponse(template.render(ctx))
    
###################################################################################

def _get_user_state(request):
    try:    
        stored_state = ActivityState.objects.get(user=request.user)
    except ActivityState.DoesNotExist:
        # setup the template
        patients = Patient.objects.all().order_by('display_order')
        state = {}
        state['version'] = 1
        state['patients'] = {}
        
        stored_state = ActivityState.objects.create(user=request.user, json=simplejson.dumps(state))

    return simplejson.loads(stored_state.json)

def _save_user_state(request, patient_id):
    if (len(request.POST['json']) < 1):
        return
    
    user_state = _get_user_state(request)
    
    if (not user_state['patients'].has_key(patient_id)):
        user_state['patients'][patient_id] = {}

    # add the posted information to the user_state
    updated_state = simplejson.loads(request.POST['json'])
    for item in updated_state:
        user_state['patients'][patient_id][item] = updated_state[item]
    
    _save(request, user_state)
    
def _save_my_place(request):
    user_state = _get_user_state(request)
    user_state['path'] = request.path
    _save(request, user_state)
    
def _save(request, user_state):
    stored_state = ActivityState.objects.get(user=request.user)
    stored_state.json = simplejson.dumps(user_state)
    stored_state.save()
    
def _is_combination(user_state, patient_id):
    return user_state['patients'][patient_id]['prescribe'] == 'combination'

    
###################################################################################

def _get_next_page(page_id):
    next_page = ""
    if (page_id == "options"):
        next_page = "selection"
    elif (page_id == "selection"):
        next_page = "prescription"
    elif (page_id == "prescription"):
        next_page = "results"
    return next_page

def _get_next_patient(patient_id):
    try:
        current_patient = Patient.objects.get(id=patient_id)
        next_patient = Patient.objects.get(display_order = current_patient.display_order + 1)
        return next_patient
    except Patient.DoesNotExist:
        return None
        
def _get_previous_patient(patient_id):
    try:
        current_patient = Patient.objects.get(id=patient_id)
        next_patient = Patient.objects.get(display_order = current_patient.display_order - 1)
        return next_patient
    except Patient.DoesNotExist:
        return None    