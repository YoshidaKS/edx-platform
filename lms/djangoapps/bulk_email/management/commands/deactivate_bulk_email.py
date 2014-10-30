"""
Deactivate bulk_email by email address or username.
"""
import json
from datetime import datetime
from optparse import make_option

import boto.sqs
from boto.sqs.message import RawMessage
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from student.models import CourseEnrollment, get_user_by_username_or_email
from bulk_email.models import Optout


class Command(BaseCommand):
    """
    Django management command to deactivate bulk_email by email address or username
    """
    help = '''Deactivate bulk_email by email address or username'''
    args = '<email or username>'
    option_list = BaseCommand.option_list + (
        make_option('-c', '--course_id',
                    metavar="COURSE_ID",
                    dest='spec_course_id',
                    default=False,
                    help="Change specific course state"),
        make_option('-r', '--reactivate',
                    action="store_true",
                    dest='reactivate',
                    default=False,
                    help='Reactivates bulk_email (change force_diabled to False)'),
        make_option('--sqs',
                    action='store_true',
                    dest='sqs',
                    default=False,
                    help="get bounced Email addresses from SQS and deactivate")
    )

    def handle(self, *args, **options):
        spec_course_id = options['spec_course_id']
        reactivate = options['reactivate']
        sqs = options['sqs']
        if sqs == True:
            conn = boto.sqs.connect_to_region(
                 "ap-northeast-1",
                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            queue = conn.create_queue("testqueue")
            queue.set_attribute('ReceiveMessageWaitTimeSeconds', 20)
            queue.set_message_class(RawMessage)
            msgs = queue.get_messages(10)
            for msg in msgs:
		body = json.loads(json.loads(msg.get_body())["Message"])
                email = body["bounce"]["bouncedRecipients"][0]["emailAddress"] 
                print ('email: {}').format(email)
                try:
                    user = get_user_by_username_or_email(email)
                except:
                    print ('nouser_email: {}').format(email)
            raise CommandError('[[must make bulk_email deactivate process here]]Email from SQS Normally Aborted')
        else:
            if len(args) != 1:
                raise CommandError('Must called with arguments: {}'.format(self.args))
        try:
            user = get_user_by_username_or_email(args[0])
        except:
            raise CommandError('No user exists [ {} ]'.format(args[0]))

        if spec_course_id:
            self.change_optout_state(user, spec_course_id, reactivate)
        else:
            course_enrollments = CourseEnrollment.enrollments_for_user(user)
            for enrollment in course_enrollments:
                course_id = enrollment.course_id
                self.change_optout_state(user, course_id, reactivate)

    def change_optout_state(self, user, course_id, reactivate):
        optout_object = Optout.objects.filter(user=user, course_id=course_id)
        if reactivate:
            optout_object.delete()
            print ('Activating: {}').format(course_id)
        else:
            if not optout_object:
                Optout.objects.create(user=user, course_id=course_id, force_disabled=True)
                print ('Force Deactivating: {}').format(course_id)
            else:
                update_optout = Optout.objects.filter(user=user, course_id=course_id, force_disabled=False).update(force_disabled=True)
                if update_optout:
                    print ('Updated force_disabled flag: {}').format(course_id)
