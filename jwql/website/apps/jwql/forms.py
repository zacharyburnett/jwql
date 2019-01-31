"""Defines the forms for the ``jwql`` web app.

Django allows for an object-oriented model representation of forms for
users to provide input through HTTP POST methods. This module defines
all of the forms that are used across the various webpages used for the
JWQL application.

Authors
-------

    - Lauren Chambers
    - Johannes Sahlmann

Use
---

    This module is used within ``views.py`` as such:
    ::
        from .forms import FileSearchForm
        def view_function(request):
            form = FileSearchForm(request.POST or None)

            if request.method == 'POST':
                if form.is_valid():
                    # Process form input and redirect
                    return redirect(new_url)

            template = 'some_template.html'
            context = {'form': form, ...}
            return render(request, template, context)

References
----------
    For more information please see:
        ``https://docs.djangoproject.com/en/2.1/topics/forms/``

Dependencies
------------
    The user must have a configuration file named ``config.json``
    placed in the ``jwql/utils/`` directory.
"""

import glob
import os

from astropy.time import Time, TimeDelta
from django import forms
from django.shortcuts import redirect

from jwql.utils.constants import JWST_INSTRUMENT_NAMES_SHORTHAND
from jwql.utils.engineering_database import is_valid_mnemonic
from jwql.utils.utils import get_config, filename_parser

FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')


class FileSearchForm(forms.Form):
    """A form that contains a single field for users to search for a proposal
    or fileroot in the JWQL filesystem.
    """
    # Define search field
    search = forms.CharField(label='', max_length=500, required=True,
                             empty_value='Search')

    # Initialize attributes
    fileroot_dict = None
    search_type = None
    instrument = None

    def clean_search(self):
        """Validate the "search" field by checking to ensure the input
        is either a proposal or fileroot, and one that matches files
        in the filesystem.

        Returns
        -------
        str
            The cleaned data input into the "search" field
        """
        # Get the cleaned search data
        search = self.cleaned_data['search']

        # Make sure the search is either a proposal or fileroot
        if len(search) == 5 and search.isnumeric():
            self.search_type = 'proposal'
        elif self._search_is_fileroot(search):
            self.search_type = 'fileroot'
        else:
            raise forms.ValidationError('Invalid search term {}. Please provide proposal number or file root.'.format(search))

        # If they searched for a proposal...
        if self.search_type == 'proposal':
            # See if there are any matching proposals and, if so, what
            # instrument they are for
            search_string = os.path.join(FILESYSTEM_DIR, 'jw{}'.format(search),
                                         '*{}*.fits'.format(search))
            all_files = glob.glob(search_string)
            if len(all_files) > 0:
                all_instruments = []
                for file in all_files:
                    instrument = filename_parser(file)['detector']
                    all_instruments.append(instrument[:3])
                if len(set(all_instruments)) > 1:
                    raise forms.ValidationError('Cannot return result for proposal with multiple instruments.')

                self.instrument = JWST_INSTRUMENT_NAMES_SHORTHAND[all_instruments[0]]
            else:
                raise forms.ValidationError('Proposal {} not in the filesystem.'.format(search))

        # If they searched for a fileroot...
        elif self.search_type == 'fileroot':
            # See if there are any matching fileroots and, if so, what
            # instrument they are for
            search_string = os.path.join(FILESYSTEM_DIR, search[:7], '{}*.fits'.format(search))
            all_files = glob.glob(search_string)

            if len(all_files) == 0:
                raise forms.ValidationError('Fileroot {} not in the filesystem.'.format(search))

            instrument = search.split('_')[-1][:3]
            self.instrument = JWST_INSTRUMENT_NAMES_SHORTHAND[instrument]

        return self.cleaned_data['search']

    def _search_is_fileroot(self, search):
        """Determine if a search value is formatted like a fileroot.

        Parameters
        ----------
        search : str
            The search term input by the user.

        Returns
        -------
        bool
            Is the search term formatted like a fileroot?
        """
        try:
            self.fileroot_dict = filename_parser(search)
            return True
        except ValueError:
            return False

    def redirect_to_files(self):
        """Determine where to redirect the web app based on user search input.

        Returns
        -------
        HttpResponseRedirect object
            Outgoing redirect response sent to the webpage
        """

        # Process the data in form.cleaned_data as required
        search = self.cleaned_data['search']

        # If they searched for a proposal
        if self.search_type == 'proposal':
            return redirect('/{}/archive/{}'.format(self.instrument, search))

        # If they searched for a file root
        elif self.search_type == 'fileroot':
            return redirect('/{}/{}'.format(self.instrument, search))


class MnemonicSearchForm(forms.Form):
    """A single-field form to search for a mnemonic in the DMS EDB."""
    # Define search field
    search = forms.CharField(label='', max_length=500, required=True,
                             empty_value='Search')
                #, help_text="Enter the mnemonic identifier."

    # Initialize attributes
    search_type = None

    def clean_search(self):
        """Validate the "search" field by checking that the input
        is a valid mnemonic identifier.

        Returns
        -------
        str
            The cleaned data input into the "search" field
        """
        # Get the cleaned search data
        search = self.cleaned_data['search']

        # Make sure the search is a valid mnemonic identifier
        if _is_valid_mnemonic(search):
            self.search_type = 'mnemonic'
        else:
            raise forms.ValidationError('Invalid search term {}. Please enter a valid DMS EDB '
                                        'mnemonic.'.format(search))

        return self.cleaned_data['search']


class MnemonicQueryForm(forms.Form):
    """A triple-field form to query mnemonic records in the DMS EDB."""

    # times for default query
    now = Time.now()
    delta_day = -7.
    range_day = 1.
    default_start_time = now + TimeDelta(delta_day, format='jd')
    default_end_time = now + TimeDelta(delta_day+range_day, format='jd')

    # Define search fields
    search = forms.CharField(label='mnemonic', max_length=500, required=True, empty_value='Search', help_text="Enter the mnemonic identifier.")
    start_time = forms.CharField(label='start', max_length=500, required=False, initial=default_start_time.iso, help_text="Enter the start date.")
    end_time = forms.CharField(label='end', max_length=500, required=False, initial=default_end_time, help_text="Enter the end date.")


    # Initialize attributes
    # fileroot_dict = None
    search_type = None
    # instrument = None

    def clean_search(self):
        """Validate the "search" field by checking that the input
        is a valid mnemonic identifier.

        Returns
        -------
        str
            The cleaned data input into the "search" field
        """
        # Get the cleaned search data
        search = self.cleaned_data['search']

        if _is_valid_mnemonic(search):
            self.search_type = 'mnemonic'
        else:
            raise forms.ValidationError('Invalid search term {}. Please enter a valid DMS EDB '
                                        'mnemonic.'.format(search))

        return self.cleaned_data['search']

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        try:
            Time(start_time, format='iso')
        except ValueError:
            raise forms.ValidationError('Invalid time {}. Please enter a time in iso format, e.g.'
                                        '2019-01-16T00:01:00.000.'.format(start_time))
        return self.cleaned_data['start_time']

    def clean_end_time(self):
        end_time = self.cleaned_data['end_time']
        try:
            Time(end_time, format='iso')
        except ValueError:
            raise forms.ValidationError('Invalid time {}. Please enter a time in iso format, e.g.'
                                        '2019-01-16T00:01:00.000.'.format(end_time))
        return self.cleaned_data['end_time']

def _is_valid_mnemonic(mnemonic):
    """Determine if a search value is a valid EDB mnemonic.

    Parameters
    ----------
    mnemonic : str
        The search term input by the user.

    Returns
    -------
    bool
        Is the search term a valid EDB mnemonic?
    """
    return is_valid_mnemonic(mnemonic)
