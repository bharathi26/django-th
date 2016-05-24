# coding: utf-8
import evernote.edam.type.ttypes as Types
from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException
from evernote.edam.error.ttypes import EDAMErrorCode

from django.utils.translation import ugettext as _
from django.utils.log import getLogger
from django.core.cache import caches

logger = getLogger('django_th.trigger_happy')
cache = caches['th_evernote']

def get_note():
    try:
        note_store = self.client.get_note_store()
    except EDAMSystemException as e:
        # rate limite reach have to wait 1 hour !
        if e.errorCode == EDAMErrorCode.RATE_LIMIT_REACHED:
            sentence = "Rate limit reached {code}\n" \
                       "Retry your request in {msg} seconds\n" \
                       " - date set to cache again until limit reached"
            logger.warn(sentence.format(
                code=e.errorCode,
                msg=e.rateLimitDuration))
            # put again in cache the data that could not be
            # published in Evernote yet
            cache.set('th_evernote_' + str(trigger_id),
                      data,
                      version=2)
            return True
        else:
            logger.critical(e)
            return False
    except Exception as e:
        logger.critical(e)
        return False


def get_notebook(note_store, my_notebook):
    """
        get the notebook from its name
    """
    notebook_id = 0
    notebooks = note_store.listNotebooks()
    # get the notebookGUID ...
    for notebook in notebooks:
        if notebook.name.lower() == my_notebook.lower():
            notebook_id = notebook.guid
            break
    return notebook_id


def set_notebook(note_store, my_notebook, notebook_id):
    """
        create a notebook
    """
    if notebook_id == 0:
        new_notebook = Types.Notebook()
        new_notebook.name = my_notebook
        new_notebook.defaultNotebook = False
        notebook_id = note_store.createNotebook(new_notebook).guid
    return notebook_id


def get_tag(note_store, my_tags):
    """
        get the tags from his Evernote account
        :param note_store Evernote Instance
        :param my_tags string
        :return: array of the tag to create
    """
    tag_id = []
    listtags = note_store.listTags()
    # cut the string by piece of tag with comma
    if ',' in my_tags:
        for my_tag in my_tags.split(','):
            for tag in listtags:
                # remove space before and after
                # thus we keep "foo bar"
                # but not " foo bar" nor "foo bar "
                if tag.name.lower() == my_tag.lower().lstrip().rstrip():
                    tag_id.append(tag.guid)
                    break
    else:
        for tag in listtags:
            if tag.name.lower() == my_tags.lower():
                tag_id.append(tag.guid)
                break

    return tag_id


def set_tag(note_store, my_tags, tag_id):
    """
        create a tag if not exists
        :param note_store evernote instance
        :param my_tags string
        :param tag_id id of the tag(s) to create
        :return: array of the tag to create
    """
    new_tag = Types.Tag()
    if ',' in my_tags:
        for my_tag in my_tags.split(','):
            new_tag.name = my_tag
            tag_id.append(create_tag(note_store, new_tag))
    elif my_tags:
        new_tag.name = my_tags
        tag_id.append(create_tag(note_store, new_tag))

    return tag_id


def create_note(note_store, note, trigger_id, data):
    """
        create a note
        :param note_store Evernote instance
        :param note
        :param trigger_id id of the trigger
        :param data to save or to put in cache
        :type note_store: Evernote Instance
        :type note: Note instance
        :type trigger_id: int
        :type data: dict
        :return boolean
        :rtype boolean
    """
    # create the note !
    try:
        created_note = note_store.createNote(note)
        sentence = str('note %s created') % created_note.guid
        logger.debug(sentence)
        return True
    except EDAMSystemException as e:
        if e.errorCode == EDAMErrorCode.RATE_LIMIT_REACHED:
            sentence = "Rate limit reached {code} " \
                       "Retry your request in {msg} seconds"
            logger.warn(sentence.format(
                code=e.errorCode,
                msg=e.rateLimitDuration))
            # put again in cache the data that could not be
            # published in Evernote yet
            cache.set('th_evernote_' + str(trigger_id), data, version=2)
            return True
        else:
            logger.critical(e)
            return False
    except EDAMUserException as e:
        if e.errorCode == EDAMErrorCode.ENML_VALIDATION:
            sentence = "Data ignored due to validation" \
                       " error : err {code} {msg}"
            logger.warn(sentence.format(
                code=e.errorCode,
                msg=e.parameter))
            return True
    except Exception as e:
        logger.critical(e)
        return False


def create_tag(note_store, new_tag):
    """
        :param note_store Evernote instance
        :param new_tag: create this new tag
        :return: new tag id
    """
    try:
        return note_store.createTag(new_tag).guid
    except EDAMUserException as e:
        if e.errorCode == EDAMErrorCode.DATA_CONFLICT:
            logger.info("Evernote Data Conflict Err {0}".format(e))
        elif e.errorCode == EDAMErrorCode.BAD_DATA_FORMAT:
            logger.critical("Evernote Err {0}".format(e))


def set_header():
    """
        preparing the hearder of Evernote
    """
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<!DOCTYPE en-note SYSTEM ' \
           '"http://xml.evernote.com/pub/enml2.dtd">\n'


def set_note_attribute(data):
    """
       add the link of the 'source' in the note
    """
    na = False
    if data.get('link'):
        na = Types.NoteAttributes()
        # add the url
        na.sourceURL = data.get('link')
        # add the object to the note
    return na


def set_note_footer(data, trigger):
    """
        handle the footer of the note
    """
    footer = ''
    if data.get('link'):
        provided_by = _('Provided by')
        provided_from = _('from')
        footer_from = "<br/><br/>{} <em>{}</em> {} <a href='{}'>{}</a>"

        footer = footer_from.format(
            provided_by, trigger.trigger.description, provided_from,
            data.get('link'), data.get('link'))

    return footer